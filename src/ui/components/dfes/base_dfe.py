"""Module for the base DFE classes and utilities."""

import contextlib
import datetime
import re
import typing

import pandas as pd
import streamlit as st

from domain import entities, query
from ui import data_client, ss_keys
from ui.components.buttons import add_button, constants, filter_button
from ui.models import frontend_models

if typing.TYPE_CHECKING:
    from ui.components.dfes import constants as dfe_constants


class DFE:
    """A self-contained dataframe editor component.

    Handles data loading, add/filter buttons, the st.data_editor widget,
    and syncing edits to the backend.
    """

    def __init__(self, config: frontend_models.DFEConfig) -> None:
        """Initialize the DFE from a config object."""
        self._config = config
        table_names = config.table_names

        self._write_table = table_names.write_table
        self._read_table = table_names.read_table or table_names.write_table
        self._key_prefix = table_names.key_prefix or table_names.write_table
        self._configs: list[frontend_models.DFEColumnConfigBase] = list(config.configs)
        self._backend_model = config.backend_model
        self._sample_data = config.sample_data
        self._tables_to_clear: list[dfe_constants.TableNames] | None = (
            config.tables_to_clear
        )
        self._num_rows = config.num_rows

        # Computed once — display config never changes with filter state
        self._column_config = {
            cfg.column_name: cfg.column_config for cfg in self._configs
        }

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def key_prefix(self) -> str:
        """The session state key prefix for this DFE."""
        return self._key_prefix

    @property
    def write_table(self) -> str:
        """The write table name for this DFE."""
        return self._write_table

    @property
    def working_df(self) -> pd.DataFrame | None:
        """Get the working dataframe from session state."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        return st.session_state.get(key, None)

    @working_df.setter
    def working_df(self, df: pd.DataFrame) -> None:
        """Set the working dataframe in session state."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        st.session_state[key] = df

    @property
    def backend_updates(self) -> entities.BackendUpdates:
        """Get pending backend updates for this DFE."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        return st.session_state.get(key, entities.BackendUpdates())

    @backend_updates.setter
    def backend_updates(self, updates: entities.BackendUpdates) -> None:
        key = f"{self._key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        st.session_state[key] = updates

    @property
    def add_button(self) -> add_button.AddButton:
        """Create a configured AddButton for this DFE."""
        return add_button.AddButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            backend_model=self._backend_model,
            tables_to_clear=self._tables_to_clear,
            extra_row_values=self._config.extra_row_values,
        )

    @property
    def filter_button(self) -> filter_button.FilterButton:
        """Create a configured FilterButton for this DFE."""
        return filter_button.FilterButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            read_table=self._read_table,
        )

    @property
    def writable_configs(self) -> list[frontend_models.DFEColumnConfig]:
        """Get the writable column configs for use with AddButton."""
        return [
            c
            for c in self._configs
            if isinstance(c, frontend_models.DFEColumnConfig) and c.visible
        ]

    @property
    def all_configs(self) -> list[frontend_models.DFEColumnConfigBase]:
        """Get all column configs for use with FilterButton."""
        return list(self._configs)

    # ------------------------------------------------------------------
    # Private properties
    # ------------------------------------------------------------------

    def _clear_working_df(self) -> None:
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        if key in st.session_state:
            del st.session_state[key]

    @property
    def _active_configs(self) -> list[frontend_models.DFEColumnConfigBase]:
        """Get the active configs (with current filter state from session)."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}"
        return st.session_state.get(key, self._configs)

    @property
    def _editor_state(self) -> dict[str, typing.Any]:
        return st.session_state[self._key_prefix]

    @property
    def _edited_rows(self) -> dict[str, dict[str, typing.Any]]:
        return self._editor_state[ss_keys.SSKeys.EDITED_ROWS]

    @property
    def _deleted_rows(self) -> list[int]:
        return self._editor_state[ss_keys.SSKeys.DELETED_ROWS]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_input_data(self) -> typing.Self:
        """Load data into the dataframe editor.

        Uses the active filter state from session and the sample_data from config
        as fallback when no data is returned.
        """
        if self.working_df is None:
            working_df = pd.DataFrame(
                data_client.get_data(
                    table_name=self._read_table,
                    query_string="*",
                    _configs=self._active_configs,
                ),
            )
            if working_df.empty:
                working_df = self._sample_data.copy()
            working_df = self._convert_cols_to_datetime(working_df)
            self.working_df = working_df

        return self

    def render_buttons(self) -> tuple[bool, bool]:
        """Render the add and filter buttons for this DFE.

        Returns:
            A tuple of (data_added, filters_changed).

        """
        if self.working_df is None:
            msg = "Call load_input_data() before render_buttons()."
            raise ValueError(msg)

        filter_btn = filter_button.FilterButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            read_table=self._read_table,
        )

        data_added = False
        filters_changed = False
        if self._num_rows != "fixed":
            add_btn = add_button.AddButton(
                table_name=self._write_table,
                key_prefix=self._key_prefix,
                backend_model=self._backend_model,
                tables_to_clear=self._tables_to_clear,
                extra_row_values=getattr(self._config, "extra_row_values", None),
            )
            writable_configs = [
                c
                for c in self._configs
                if isinstance(c, frontend_models.DFEColumnConfig) and c.visible
            ]
            add_col, filter_col, _ = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)
            with add_col:
                data_added = add_btn(col_configs=writable_configs)
            with filter_col:
                filters_changed = filter_btn(col_configs=self._configs)
        else:
            filter_col, _ = st.columns([1, 5])
            with filter_col:
                filters_changed = filter_btn(col_configs=self._configs)

        return data_added, filters_changed

    def refresh(
        self,
        *,
        filters_changed: bool = False,
        data_added: bool = False,
    ) -> None:
        """Refresh the working dataframe if buttons triggered changes."""
        if filters_changed:
            data_client.invalidate_table_cache(self._read_table)

        if filters_changed or data_added:
            self._clear_working_df()
            self.load_input_data()

    def render_editor(self) -> None:
        """Render the st.data_editor widget."""
        if self.working_df is None:
            msg = "Call load_input_data() before render_editor()."
            raise ValueError(msg)
        st.data_editor(
            self.working_df,
            key=self._key_prefix,
            column_config=self._column_config,
            column_order=[col.column_name for col in self._configs if col.visible],
            num_rows=self._num_rows,
            hide_index=True,
            on_change=self.sync,
        )

    def sync(self) -> None:
        """Prep backend updates for syncing."""
        if self.working_df is None:
            msg = "Working dataframe is not initialized. Cannot sync."
            raise ValueError(msg)

        unique_col_names = [
            col.column_name
            for col in self._configs
            if isinstance(col, frontend_models.DFEColumnConfig) and col.enforce_unique
        ]

        beu_edited_rows = self._get_edited_rows_for_backend(
            unique_col_names=unique_col_names,
            working_df=self.working_df,
        )
        beu_deleted_rows = self._get_deleted_rows_for_backend(self.working_df)

        if beu_edited_rows or beu_deleted_rows:
            filters_changed, modified_df = self._check_for_filters_updates(
                working_df=self.working_df,
            )
            if filters_changed:
                self.working_df = modified_df

        self.backend_updates = entities.BackendUpdates(
            edited_rows=beu_edited_rows,
            deleted_rows=beu_deleted_rows,
        )

    def _convert_cols_to_datetime(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to datetime/date based on column config type."""
        for config in self._configs:
            col = config.column_name
            if col not in dataframe.columns:
                continue
            if not isinstance(config.column_config, dict):
                continue
            col_type = config.column_config.get("type_config", {}).get("type")
            if col_type == "date":
                with contextlib.suppress(Exception):
                    dataframe[col] = pd.to_datetime(dataframe[col]).dt.date
            elif col_type == "datetime":
                with contextlib.suppress(Exception):
                    dataframe[col] = pd.to_datetime(dataframe[col])
        return dataframe

    @staticmethod
    def _get_pandas_filters(filters: query.Filters) -> dict[str, object]:
        """Serialise to pandas friendly format."""
        serialised: dict[str, query.FilterValue | list[query.FilterValue] | str] = (
            filters.model_dump(exclude_none=True)
        )
        to_pandas_map = {
            "eq": "==",
            "lt": "<",
            "lte": "<=",
            "gt": ">",
            "gte": ">=",
        }
        serialised_pandas = {}
        for key, value in serialised.items():
            if key in to_pandas_map:
                serialised_pandas[to_pandas_map[key]] = value
            else:
                serialised_pandas[key] = value
        return serialised_pandas

    @staticmethod
    def _apply_column_filter(
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
        if isinstance(criteria, datetime.date):
            converted_col = pd.to_datetime(modified_df[col])
            criteria_ts = pd.Timestamp(criteria)
            ops = {">=": "ge", "<=": "le", ">": "gt", "<": "lt"}
            mask = getattr(converted_col, ops[operator])(criteria_ts)
            return modified_df.loc[mask]
        return modified_df.query(f"`{col}` {operator} @criteria")

    def _check_for_filters_updates(
        self,
        working_df: pd.DataFrame,
    ) -> tuple[bool, pd.DataFrame]:
        """Check if editor changes fall outside current filters."""
        modified_df = working_df.copy()

        if self._deleted_rows:
            modified_df = modified_df.drop(self._deleted_rows).reset_index(drop=True)

        for row_idx, changes in self._edited_rows.items():
            if int(row_idx) < len(modified_df):
                for col, value in changes.items():
                    modified_df.at[int(row_idx), col] = value  # noqa: PD008

        for config in self._active_configs:
            if config.filters and config.column_name in modified_df.columns:
                filters = self._get_pandas_filters(config.filters)
                for operator, criteria in filters.items():
                    modified_df = self._apply_column_filter(
                        modified_df,
                        config.column_name,
                        operator,
                        criteria,
                    )

        changed = len(modified_df) != len(working_df)
        return changed, modified_df.reset_index(drop=True)

    def _enforce_unique_cols(
        self,
        row: dict[str, typing.Any],
        unique_col_names: list[str],
    ) -> dict[str, typing.Any]:
        """Process a single row to enforce unique constraints."""
        for col in unique_col_names:
            if col not in row:
                continue

            unique_values = set(
                data_client.get_column_values(
                    table_name=self._write_table,
                    column_name=col,
                    unique=True,
                ),
            )
            base_value = re.sub(r" \(\d+\)$", "", str(row[col]))
            duplicates = [
                str(v) for v in unique_values if str(v).startswith(base_value)
            ]
            if duplicates:
                suffixes: list[int] = []
                for val in duplicates:
                    match = re.search(r" \((\d+)\)$", val)
                    if match:
                        with contextlib.suppress(ValueError):
                            suffixes.append(int(match.group(1)))
                max_suffix = max(suffixes) if suffixes else 0
                row[col] = f"{base_value} ({max_suffix + 1})"
        return row

    def _get_edited_rows_for_backend(
        self,
        unique_col_names: list[str],
        working_df: pd.DataFrame,
    ) -> dict[str, dict[str, typing.Any]]:
        """Get backend updates for edited rows."""
        beu_edited_rows: dict[str, dict[str, typing.Any]] = {}
        for row_idx, changes in self._edited_rows.items():
            unique_changes = self._enforce_unique_cols(
                row=changes,
                unique_col_names=unique_col_names,
            )
            row_id = working_df.iloc[int(row_idx)]["id"]
            beu_edited_rows[row_id] = unique_changes
        return beu_edited_rows

    def _get_deleted_rows_for_backend(self, working_df: pd.DataFrame) -> list[str]:
        """Get backend updates for deleted rows."""
        beu_deleted_rows: list[str] = []
        for row_idx in self._deleted_rows:
            row_id = working_df.iloc[row_idx]["id"]
            beu_deleted_rows.append(row_id)
        return beu_deleted_rows
