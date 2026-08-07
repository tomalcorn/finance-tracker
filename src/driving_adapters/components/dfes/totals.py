"""The totals strip: a one-row table of column sums beneath a grid.

Its own table rather than an extra row in the editor, so it stays put while the
grid scrolls and never has to be told apart from real rows when the editor's
deltas are mapped back onto the rows they came from.

Two Streamlit constraints shape how it is rendered, both measured rather than
assumed:

- **It is a ``st.data_editor``, with every column disabled.** Styles from a
  pandas ``Styler`` are applied only to *non-editable* columns, so a disabled
  editor is the only table whose every cell can be bold. A ``st.dataframe``
  bolds them too, but see the next point.
- **Alignment needs the same table type, the same widths, and the same
  ``num_rows``.** A grid that allows row deletion draws a fixed 32px
  row-marker gutter that a ``st.dataframe`` has no equivalent for, and when a
  table stretches to its container the leftover space is shared equally between
  its columns — so a strip with a different column count drifts out of line.
  Matching the editor on all three lines the two up to the pixel, at any window
  width, with both still stretching to fill the page.

Which columns are summed is the block's choice, via ``DFEColumnConfig.total``.
"""

from typing import TYPE_CHECKING, Literal

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from driving_adapters.models import frontend_models

_LABEL = "Total"

_BLANK = ""

_BOLD = "font-weight: bold"

_KEY_SUFFIX = "_totals"


def _visible_columns(
    grid_display: "frontend_models.GridDisplay",
) -> list["frontend_models.DFEColumnConfig"]:
    """Return the columns the grid actually shows, in display order."""
    return [column for column in grid_display.columns if column.visible]


def _column_sum(working_df: pd.DataFrame, column_name: str) -> float:
    """Sum one column of the display frame, ignoring anything non-numeric."""
    if column_name not in working_df.columns:
        return 0.0
    return float(pd.to_numeric(working_df[column_name], errors="coerce").sum())


def build_totals_df(
    grid_display: "frontend_models.GridDisplay",
    working_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build the one-row totals frame for a grid, empty if it has no totals.

    Every visible column is present so the totals line up with the columns
    above; the ones that are not summed are blank. The frame comes back empty
    when there is nothing to show: no column asks to be totalled, or the grid is
    displaying its empty-state sample data (no ``id`` column), whose example
    figures would read as real money.

    Args:
        grid_display: The display half of the grid config.
        working_df: The frame the editor is rendering, filters already applied.

    Returns:
        The one-row totals frame, empty when there is nothing to total.

    """
    columns = _visible_columns(grid_display)
    if not any(column.total for column in columns):
        return pd.DataFrame()
    if working_df.empty or "id" not in working_df.columns:
        return pd.DataFrame()

    row: dict[str, object] = {
        column.column_name: (
            _column_sum(working_df, column.column_name) if column.total else _BLANK
        )
        for column in columns
    }
    _name_the_row(row)
    return pd.DataFrame([row])


def _name_the_row(row: dict[str, object]) -> None:
    """Name the strip in its first blank column, so the row reads as a total."""
    for column_name, value in row.items():
        if value == _BLANK:
            row[column_name] = _LABEL
            return


def build_column_config(
    grid_display: "frontend_models.GridDisplay",
) -> dict[str, "frontend_models.StreamlitColumnConfig"]:
    """Build the totals strip's column config from the grid's own.

    A summed column keeps the grid's config, so its figure is formatted and
    sized exactly like the column above it. Every other column is re-declared as
    text — its cell is blank, and a blank number or date renders as "None".

    Every column is disabled, for two reasons: nothing in the strip is an input,
    and Streamlit applies a ``Styler``'s styles only to non-editable columns, so
    this is also what lets the whole row be bold.

    Args:
        grid_display: The display half of the grid config.

    Returns:
        The column config keyed by column name, for the visible columns.

    """
    column_config: dict[str, frontend_models.StreamlitColumnConfig] = {}
    for column in _visible_columns(grid_display):
        original = (
            column.column_config if isinstance(column.column_config, dict) else {}
        )
        if column.total:
            column_config[column.column_name] = {**original, "disabled": True}
            continue
        column_config[column.column_name] = st.column_config.TextColumn(
            original.get("label"),
            width=original.get("width"),
            disabled=True,
        )
    return column_config


def strip_num_rows(
    grid_display: "frontend_models.GridDisplay",
) -> Literal["fixed", "delete"]:
    """Match the grid's row-marker gutter, which the strip has to line up with.

    A grid that allows row deletion draws the gutter; one that does not, does
    not. ``"delete"`` rather than the grid's own ``"dynamic"`` where it has one:
    same gutter, without the trailing blank row an editor offers for adding.
    """
    return "fixed" if grid_display.num_rows == "fixed" else "delete"


def render(
    grid_display: "frontend_models.GridDisplay",
    key_prefix: str,
    working_df: pd.DataFrame,
) -> None:
    """Render the totals strip beneath a grid, when the grid has one."""
    totals_df = build_totals_df(grid_display, working_df)
    if totals_df.empty:
        return
    key = f"{key_prefix}{_KEY_SUFFIX}"
    # The strip is display, not input, so it keeps no state between runs. Its
    # widget state is dropped rather than read: an editor still lets a row be
    # deleted however disabled its columns are, and that deletion would
    # otherwise persist in session state and hide the totals for the session.
    st.session_state.pop(key, None)
    st.data_editor(
        totals_df.style.map(lambda _cell: _BOLD),
        key=key,
        column_config=build_column_config(grid_display),
        column_order=[column.column_name for column in _visible_columns(grid_display)],
        num_rows=strip_num_rows(grid_display),
        hide_index=True,
    )
