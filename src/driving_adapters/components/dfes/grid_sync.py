"""Pure edit/diff/sync logic for the dataframe editor, free of Streamlit.

These functions translate the raw ``st.data_editor`` deltas (edited and
deleted rows) plus the active filter state into backend updates and a
re-filtered working frame. They take everything they need as arguments —
no ``st.*`` access and no session state — so they can be unit-tested
without a Streamlit runtime.
"""

import datetime
import re
import typing
from collections.abc import Callable

import pandas as pd

from domain import entities, query

if typing.TYPE_CHECKING:
    from driving_adapters.models import frontend_models

UniqueChecker = Callable[[str], set[object]]
"""Returns the set of existing values for a column (user-scoped)."""

_INSERTION_COLUMN = "created_at"
"""Trailing sort key: when the row was inserted.

Its direction is the grid's own (``GridDisplay.insertion_sorting``), so a grid
can put its newest rows either side of the ones it ties with.
"""

_UNIQUE_COLUMN = "id"
"""Final sort key, always ascending: settles whatever the keys before it tie on.

Both trailing keys are absent from the sample-data empty state, which is why
each is applied only when the frame actually carries it.
"""

_TO_PANDAS_OPERATOR = {
    "eq": "==",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
}


def pandas_filters(filters: query.Filters) -> dict[str, object]:
    """Serialise a Filters model into a pandas-friendly operator map."""
    serialised: dict[str, query.FilterValue | list[query.FilterValue] | str] = (
        filters.model_dump(exclude_none=True)
    )
    serialised_pandas: dict[str, object] = {}
    for key, value in serialised.items():
        serialised_pandas[_TO_PANDAS_OPERATOR.get(key, key)] = value
    return serialised_pandas


def apply_column_filter(
    modified_df: pd.DataFrame,
    col: str,
    operator: str,
    criteria: object,
) -> pd.DataFrame:
    """Apply a single filter operation to the DataFrame."""
    if operator == "contains":
        mask = modified_df[col].str.contains(str(criteria), na=False)
        return modified_df[mask]
    if operator == "cs":
        mask = modified_df[col].apply(
            lambda x, c=criteria: c in x if isinstance(x, list) else False,
        )
        return modified_df[mask]
    if operator == "in":
        selected = set(criteria) if isinstance(criteria, (list, set)) else {criteria}
        mask = modified_df[col].apply(
            lambda x, s=selected: (
                bool(s.intersection(x)) if isinstance(x, list) else x in s
            ),
        )
        return modified_df[mask]
    if isinstance(criteria, datetime.date):
        converted_col = pd.to_datetime(modified_df[col])
        criteria_ts = pd.Timestamp(criteria)
        ops = {">=": "ge", "<=": "le", ">": "gt", "<": "lt"}
        mask = getattr(converted_col, ops[operator])(criteria_ts)
        return modified_df.loc[mask]
    return modified_df.query(f"`{col}` {operator} @criteria")


def apply_active_filters(
    dataframe: pd.DataFrame,
    active_configs: list["frontend_models.DFEColumnConfig"],
) -> pd.DataFrame:
    """Apply every configured column filter to the frame, in Python (Path A)."""
    modified_df = dataframe
    for config in active_configs:
        if config.filters and config.column_name in modified_df.columns:
            for operator, criteria in pandas_filters(config.filters).items():
                modified_df = apply_column_filter(
                    modified_df,
                    config.column_name,
                    operator,
                    criteria,
                )
    return modified_df


def apply_active_sorting(
    dataframe: pd.DataFrame,
    active_configs: list["frontend_models.DFEColumnConfig"],
    insertion_sorting: query.SortingValues = query.SortingValues.ASC,
) -> pd.DataFrame:
    """Sort the frame by every column configured with a sort direction (Path A).

    Path A reads unordered rows from the port, so the ``sorting`` a column
    config declares is applied here in Python (it used to ride along on the
    SQL query). Columns are sorted in config order, then by ``created_at`` and
    ``id``, so the result depends only on the rows themselves and never on the
    order they were fetched in.

    The tiebreak is load-bearing rather than cosmetic: the editor records its
    deltas by position, and ``compute_deltas`` resolves them by position
    against a frame rebuilt on a later run. Two fetches of the same rows have
    to order them the same way, or a delta lands on the wrong row.

    Args:
        dataframe: The display frame to order.
        active_configs: The grid's columns, carrying the current sort state.
        insertion_sorting: Direction of the ``created_at`` tiebreak. ``DESC``
            puts the newest-created row first among rows tied on the sorted
            columns; the ``id`` key after it stays ascending either way, so the
            order remains total.

    Returns:
        The frame ordered by the configured columns and the trailing keys.

    """
    sort_configs = [
        config
        for config in active_configs
        if config.sorting and config.column_name in dataframe.columns
    ]
    sort_columns = [config.column_name for config in sort_configs]
    ascending = [config.sorting == query.SortingValues.ASC for config in sort_configs]
    tiebreaks = (
        (_INSERTION_COLUMN, insertion_sorting == query.SortingValues.ASC),
        (_UNIQUE_COLUMN, True),
    )
    for column, column_ascending in tiebreaks:
        if column in dataframe.columns:
            sort_columns.append(column)
            ascending.append(column_ascending)
    if not sort_columns:
        return dataframe
    return dataframe.sort_values(
        by=sort_columns,
        ascending=ascending,
        kind="stable",
    ).reset_index(drop=True)


def enforce_unique_cols(
    row: dict[str, typing.Any],
    unique_col_names: list[str],
    unique_checker: UniqueChecker,
) -> dict[str, typing.Any]:
    """Suffix a row's unique columns to avoid clashing with existing values.

    Args:
        row: The edited row values; mutated in place and returned.
        unique_col_names: Columns that must stay unique.
        unique_checker: Returns the existing (user-scoped) values for a column.

    Returns:
        The row with any clashing unique values suffixed, e.g. ``Item (1)``.

    """
    for col in unique_col_names:
        if col not in row:
            continue

        unique_values = unique_checker(col)
        base_value = re.sub(r" \(\d+\)$", "", str(row[col]))
        # Match only the base itself or the base with a numeric suffix, so
        # "Car" collides with "Car"/"Car (1)" but never with "Carpet".
        clash = re.compile(rf"^{re.escape(base_value)}(?: \((\d+)\))?$")
        matches = [m for v in unique_values if (m := clash.match(str(v)))]
        if matches:
            suffixes = [int(m.group(1)) for m in matches if m.group(1) is not None]
            max_suffix = max(suffixes) if suffixes else 0
            row[col] = f"{base_value} ({max_suffix + 1})"
    return row


def compute_deltas(
    working_df: pd.DataFrame,
    edited_rows: dict[str, dict[str, typing.Any]],
    deleted_rows: list[int],
    unique_col_names: list[str],
    unique_checker: UniqueChecker,
) -> tuple[entities.EditedRows, entities.DeletedIds]:
    """Translate the editor's positional deltas into id-keyed backend deltas.

    Edited rows are keyed by their backend ``id`` and have their unique columns
    suffixed via ``unique_checker``. Deleted rows resolve their positional index
    to a backend ``id``.

    Returns:
        The column patches keyed by row id, and the ids to delete.

    """
    edits: entities.EditedRows = {}
    for row_idx, changes in edited_rows.items():
        unique_changes = enforce_unique_cols(changes, unique_col_names, unique_checker)
        row_id = working_df.iloc[int(row_idx)]["id"]
        edits[row_id] = unique_changes

    deleted_ids: entities.DeletedIds = [
        working_df.iloc[row_idx]["id"] for row_idx in deleted_rows
    ]

    return edits, deleted_ids
