"""Module for the base DFE classes and utilities."""

import contextlib
import datetime
import re
import typing

import pandas as pd
import streamlit as st

from libs import data_client, ss_keys
from libs.models import backend_updates_model, frontend_models


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_names: frontend_models.DFETableNameConfig,
        configs: list[frontend_models.DFEColumnConfigBase],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.write_table = table_names.write_table
        self.read_table = table_names.read_table or table_names.write_table
        self.key_prefix = table_names.key_prefix or table_names.write_table
        self.configs = configs

        self._column_config = {
            config.column_name: config.column_config for config in configs
        }

    @property
    def working_df(self) -> pd.DataFrame | None:
        """Get the working dataframe from session state."""
        working_df_key = f"{self.key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        return st.session_state.get(working_df_key, None)

    @working_df.setter
    def working_df(self, df: pd.DataFrame) -> None:
        """Set the working dataframe in session state."""
        working_df_key = f"{self.key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        st.session_state[working_df_key] = df

    def _clear_working_df(self) -> None:
        """Clear the working dataframe from session state."""
        working_df_key = f"{self.key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        if working_df_key in st.session_state:
            del st.session_state[working_df_key]

    @property
    def editor_state(self) -> dict[str, typing.Any]:
        """Get the editor state from session state."""
        return st.session_state[self.key_prefix]

    @property
    def edited_rows(self) -> dict[str, dict[str, typing.Any]]:
        """Get the edited rows from the editor state."""
        return self.editor_state[ss_keys.SSKeys.EDITED_ROWS]

    @property
    def deleted_rows(self) -> list[int]:
        """Get the deleted rows from the editor state."""
        return self.editor_state[ss_keys.SSKeys.DELETED_ROWS]

    @property
    def backend_updates(self) -> backend_updates_model.BackendUpdates:
        """Get the backend updates from session state."""
        backend_updates_key = f"{self.key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        return st.session_state.get(
            backend_updates_key,
            backend_updates_model.BackendUpdates(),
        )

    @backend_updates.setter
    def backend_updates(self, updates: backend_updates_model.BackendUpdates) -> None:
        """Set the backend updates in session state."""
        backend_updates_key = f"{self.key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        st.session_state[backend_updates_key] = updates

    def load_input_data(
        self,
        sample_data: pd.DataFrame,
        *,
        filters_changed: bool,
        new_data_added: bool,
    ) -> typing.Self:
        """Load data into the dataframe editor.

        If filters have changed or new data has been added, the working
        dataframe is cleared and reloaded from the backend.

        Args:
            sample_data: Fallback data to show when the backend returns nothing.
            filters_changed: Whether the active filters have changed.
            new_data_added: Whether new rows were just added.

        """
        if filters_changed or new_data_added:
            self._clear_working_df()

        # Initialize working_df if needed
        if self.working_df is None:
            working_df = pd.DataFrame(
                data_client.get_data(
                    table_name=self.read_table,
                    query_string="*",
                    _configs=self.configs,
                ),
            )
            if working_df.empty:
                working_df = sample_data.copy()
            working_df = self._convert_cols_to_datetime(working_df)
            self.working_df = working_df

        return self

    def _convert_cols_to_datetime(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """Convert columns to datetime/date based on column config type."""
        for config in self.configs:
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
        """Check if editor changes fall outside current filters.

        Args:
            working_df: The current working DataFrame

        Returns:
            A tuple of (bool, pd.DataFrame) where the bool indicates if the DataFrame
            changed due to filtering, and the DataFrame is the possibly modified result

        """
        modified_df = working_df.copy()

        # Apply deletions
        if self.deleted_rows:
            modified_df = modified_df.drop(self.deleted_rows).reset_index(drop=True)

        # Apply edits
        for row_idx, changes in self.edited_rows.items():
            if int(row_idx) < len(modified_df):
                for col, value in changes.items():
                    modified_df.at[int(row_idx), col] = value  # noqa: PD008 - needed to assign list values to a single cell

        # Apply filters
        for config in self.configs:
            if config.filters and config.column_name in modified_df.columns:
                filters = config.filters.get_pandas_filters()
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
                    table_name=self.write_table,
                    column_name=col,
                    unique=True,
                ),
            )
            base_value = re.sub(r" \(\d+\)$", "", str(row[col]))
            # Filter unique_values for entries that start with base_value
            duplicates = [
                str(v) for v in unique_values if str(v).startswith(base_value)
            ]
            if duplicates:
                # Extract numeric suffixes like " (123)" and take the max; if none
                # found, start from 0
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
        for row_idx, changes in self.edited_rows.items():
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
        for row_idx in self.deleted_rows:
            row_id = working_df.iloc[row_idx]["id"]
            beu_deleted_rows.append(row_id)
        return beu_deleted_rows

    def sync(self) -> None:
        """Prep backend_updates.BackendUpdates for syncing."""
        if self.working_df is None:
            msg = "Working dataframe is not initialized. Cannot sync."
            raise ValueError(msg)

        unique_col_names = [
            col.column_name
            for col in self.configs
            if isinstance(col, frontend_models.DFEColumnConfig) and col.enforce_unique
        ]

        beu_edited_rows = self._get_edited_rows_for_backend(
            unique_col_names=unique_col_names,
            working_df=self.working_df,
        )
        beu_deleted_rows = self._get_deleted_rows_for_backend(self.working_df)

        if beu_edited_rows or beu_deleted_rows:
            # Apply changes to working_df and check changes still in filters
            filters_changed, modified_df = self._check_for_filters_updates(
                working_df=self.working_df,
            )
            if filters_changed:
                self.working_df = modified_df

        # in "delete" mode, so no added rows
        self.backend_updates = backend_updates_model.BackendUpdates(
            edited_rows=beu_edited_rows,
            deleted_rows=beu_deleted_rows,
        )

    def render(self) -> pd.DataFrame:
        """Render the dataframe editor with the original dataframe."""
        # Get working dataframe from session state
        if self.working_df is None:
            msg = (
                "Working dataframe is not initialized. Make sure to call "
                "load_input_data() first."
            )
            raise ValueError(msg)
        return st.data_editor(
            self.working_df,
            key=self.key_prefix,
            column_config=self._column_config,
            column_order=[col.column_name for col in self.configs if col.visible],
            num_rows="delete",
            hide_index=True,
            on_change=self.sync,
        )
