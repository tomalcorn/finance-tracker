"""Module for the base DFE classes and utilities."""

import contextlib
import re
import typing

import pandas as pd
import streamlit as st
from pandas.api import types as pd_types

from apps import data_client
from libs.models import backend_models, constants, frontend_models

MAX_UNIQUE_VALUES = 20
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}.*")


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_name: str,
        configs: list[frontend_models.DFEColumnConfigBase],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.configs = configs

        self._column_config = {
            config.column_name: config.column_config for config in configs
        }

    @property
    def working_df(self) -> pd.DataFrame | None:
        """Get the working dataframe from session state."""
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        return st.session_state.get(working_df_key, None)

    @working_df.setter
    def working_df(self, df: pd.DataFrame) -> None:
        """Set the working dataframe in session state."""
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        st.session_state[working_df_key] = df

    def _clear_working_df(self) -> None:
        """Clear the working dataframe from session state."""
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        if working_df_key in st.session_state:
            del st.session_state[working_df_key]

    @property
    def editor_state(self) -> dict[str, typing.Any]:
        """Get the editor state from session state."""
        return st.session_state[self.table_name]

    @property
    def edited_rows(self) -> dict[str, dict[str, typing.Any]]:
        """Get the edited rows from the editor state."""
        return self.editor_state[constants.SSKeys.EDITED_ROWS]

    @property
    def deleted_rows(self) -> list[int]:
        """Get the deleted rows from the editor state."""
        return self.editor_state[constants.SSKeys.DELETED_ROWS]

    @property
    def backend_updates(self) -> backend_models.BackendUpdates:
        """Get the backend updates from session state."""
        backend_updates_key = f"{self.table_name}_{constants.SSKeys.BACKEND_UPDATES}"
        return st.session_state.get(
            backend_updates_key,
            backend_models.BackendUpdates(),
        )

    @backend_updates.setter
    def backend_updates(self, updates: backend_models.BackendUpdates) -> None:
        """Set the backend updates in session state."""
        backend_updates_key = f"{self.table_name}_{constants.SSKeys.BACKEND_UPDATES}"
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
        """
        if filters_changed or new_data_added:
            self._clear_working_df()

        # Initialize working_df if needed
        if self.working_df is None:
            working_df = pd.DataFrame(
                data_client.get_data(
                    table_name=self.table_name,
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
        """Try to convert columns to datetime."""
        for col in dataframe.columns:
            if pd_types.is_object_dtype(dataframe[col]):
                sample_values = [
                    val for val in dataframe[col].to_numpy()[:10] if val is not None
                ]
                if any(DATE_PATTERN.match(str(val)) for val in sample_values):
                    with contextlib.suppress(Exception):
                        dataframe[col] = pd.to_datetime(dataframe[col])
        return dataframe

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
                    modified_df.loc[int(row_idx), col] = value

        # Apply filters
        for config in self.configs:
            if config.filters and config.column_name in modified_df.columns:
                filters = config.filters.get_pandas_filters()
                for operator, criteria in filters.items():
                    col = config.column_name

                    if operator == "contains":
                        mask = modified_df[col].str.contains(criteria, na=False)
                        modified_df = modified_df[mask]
                    else:
                        modified_df = modified_df.query(f"`{col}` {operator} @criteria")

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
                    table_name=self.table_name,
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
                suffixes = []
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
        """Prep BackendUpdates for syncing."""
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

        self.backend_updates = backend_models.BackendUpdates(
            added_rows=[],  # in "delete" mode, so no added rows
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
            key=self.table_name,
            column_config=self._column_config,
            column_order=[col.column_name for col in self.configs],
            num_rows="delete",
            hide_index=True,
            on_change=self.sync,
        )
