"""Module for the base DFE classes and utilities."""

import contextlib
import re
import typing
import uuid

import pandas as pd
import streamlit as st
from pandas.api import types as pd_types

from libs import constants, data_client, frontend_models

MAX_UNIQUE_VALUES = 20
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}.*")


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_name: str,
        configs: list[frontend_models.DFEColumnConfig],
        column_order: list[str],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.configs = configs

        self._column_config = {
            config.column_name: config.column_config for config in configs
        }
        self._column_order = column_order

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

    @property
    def previous_configs(self) -> list[frontend_models.DFEColumnConfig] | None:
        """Get the previous column configs from session state."""
        prev_configs_key = f"{self.table_name}_{constants.SSKeys.PREV_CONFIGS}"
        return st.session_state.get(prev_configs_key, None)

    @previous_configs.setter
    def previous_configs(
        self,
        configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Set the previous column configs in session state."""
        prev_configs_key = f"{self.table_name}_{constants.SSKeys.PREV_CONFIGS}"
        st.session_state[prev_configs_key] = configs

    @property
    def editor_state(self) -> dict[str, typing.Any]:
        """Get the editor state from session state."""
        return st.session_state[self.table_name]

    @property
    def added_rows(self) -> list[dict[str, typing.Any]]:
        """Get the added rows from the editor state."""
        return self.editor_state[constants.SSKeys.ADDED_ROWS]

    @property
    def edited_rows(self) -> dict[str, dict[str, typing.Any]]:
        """Get the edited rows from the editor state."""
        return self.editor_state[constants.SSKeys.EDITED_ROWS]

    @property
    def deleted_rows(self) -> list[int]:
        """Get the deleted rows from the editor state."""
        return self.editor_state[constants.SSKeys.DELETED_ROWS]

    @property
    def prev_added_rows(self) -> list[dict[str, typing.Any]]:
        """Get the previous added rows from session state."""
        prev_added_rows_key = f"{self.table_name}_{constants.SSKeys.PREV_ADDED_ROWS}"
        return st.session_state.get(prev_added_rows_key, [])

    @prev_added_rows.setter
    def prev_added_rows(self, rows: list[dict[str, typing.Any]]) -> None:
        """Set the previous added rows in session state."""
        prev_added_rows_key = f"{self.table_name}_{constants.SSKeys.PREV_ADDED_ROWS}"
        st.session_state[prev_added_rows_key] = rows

    def load_input_data(self, sample_data: pd.DataFrame) -> typing.Self:
        """Load data into the dataframe editor.

        Ideally uses the working_df from session state, but if the data served from the
        data_client is different to original_df, then flushes working_df and uses
        data_client data.
        """
        # Initialize row IDs tracking
        row_ids_key = f"{self.table_name}_{constants.SSKeys.ROW_IDS}"
        if row_ids_key not in st.session_state:
            st.session_state[row_ids_key] = []

        if self.previous_configs is None:
            self.previous_configs = self.configs

        # If change to filters or sorts, clear working_df
        if self.previous_configs != self.configs:
            self.clear_working_df()

        # Initialize working_df if needed
        if self.working_df is None:
            working_df = pd.DataFrame(
                data_client.get_data(
                    table_name=self.table_name,
                    query_string="*",
                    configs=self.configs,
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
        modified_df: pd.DataFrame,
    ) -> tuple[bool, pd.DataFrame]:
        """Check modified_df to see if changes fall outside current filters.

        Args:
            modified_df: The DataFrame to check against filters

        Returns:
            A tuple of (bool, pd.DataFrame) where the bool indicates if the DataFrame
            changed due to filtering, and the DataFrame is the possibly modified result

        """
        filtered_df = modified_df.copy()

        for config in self.configs:
            if config.filtering and config.column_name in filtered_df.columns:
                for operator, criteria in config.filtering.model_dump(
                    exclude_none=True,
                ).items():
                    col = config.column_name

                    if operator == "contains":
                        mask = filtered_df[col].str.contains(criteria, na=False)
                        filtered_df = filtered_df[mask]
                    else:
                        filtered_df = filtered_df.query(f"`{col}` {operator} @criteria")

        changed = len(filtered_df) != len(modified_df)
        return changed, filtered_df.reset_index(drop=True)

    def _check_for_sorts_updates(
        self,
        modified_df: pd.DataFrame,
        added_rows: dict[str, typing.Any] | None = None,
        edited_rows: dict[str, dict[str, typing.Any]] | None = None,
        deleted_rows: list[int] | None = None,
    ) -> tuple[bool, pd.DataFrame]:
        """Check editor_state to see if changes made to sorts columns."""
        if deleted_rows:
            return True, self._sort_columns(modified_df)

        sorts_changed = False
        for config in self.configs:
            if config.sorting is None:
                continue

            col = config.column_name
            if edited_rows:
                for changes in edited_rows.values():
                    if col in changes:
                        return True, self._sort_columns(modified_df)

            if not sorts_changed and added_rows:
                for row in added_rows:
                    if col in row:
                        return True, self._sort_columns(modified_df)
        return False, modified_df

    def _sort_columns(
        self,
        modified_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Sort the original dataframe by a list of column names."""
        sorted_df = modified_df.copy()
        for col in self.configs:
            if col.sorting is not None:
                sorted_df = sorted_df.sort_values(
                    by=col.column_name,
                    ascending=col.sorting == "asc",
                )
        return sorted_df.reset_index(drop=True)

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

    def _get_added_rows_for_backend(
        self,
        unique_col_names: list[str],
    ) -> list[dict[str, typing.Any]]:
        """Enforce unique cols, manage row IDs, return backend updates added rows."""
        beu_added_rows: list[dict[str, typing.Any]] = []
        row_ids_key = f"{self.table_name}_{constants.SSKeys.ROW_IDS}"
        row_ids: list[str] = st.session_state[row_ids_key]

        # Deal with deleted added_rows
        if len(self.added_rows) < len(row_ids):
            deleted_added_indices = [
                i
                for i, row in enumerate(self.prev_added_rows)
                if row not in self.added_rows
            ]
            for idx in sorted(deleted_added_indices, reverse=True):
                del row_ids[idx]
        self.prev_added_rows = self.added_rows

        # Assign IDs to added rows: reuse IDs from row_ids if available
        for i, row in enumerate(self.added_rows):
            unique_row = self._enforce_unique_cols(
                row=row,
                unique_col_names=unique_col_names,
            )
            if i < len(row_ids):
                unique_row["id"] = row_ids[i]
            elif "id" not in unique_row or not unique_row["id"]:
                unique_row["id"] = str(uuid.uuid4())
                beu_added_rows.append(unique_row)
        return beu_added_rows

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
            row_id = working_df.iloc[row_idx]["id"]
            beu_edited_rows[row_id] = unique_changes

    def _get_deleted_rows_for_backend(self) -> list[str]:
        """Get backend updates for deleted rows."""
        beu_deleted_rows: list[str] = []
        for row_idx in self.deleted_rows:
            row_id = self.working_df.iloc[row_idx]["id"]
            beu_deleted_rows.append(row_id)
        return beu_deleted_rows

    def clear_working_df(self) -> None:
        """Clear the working dataframe from session state."""
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        if working_df_key in st.session_state:
            del st.session_state[working_df_key]

    def sync(
        self,
        working_df: pd.DataFrame,
        modified_df: pd.DataFrame,
    ) -> frontend_models.BackendUpdates:
        """Sync the edited dataframe with the Supabase table."""
        unique_col_names = [
            col.column_name for col in self.configs if col.enforce_unique
        ]

        beu_added_rows = self._get_added_rows_for_backend(unique_col_names)
        beu_edited_rows = self._get_edited_rows_for_backend(
            unique_col_names=unique_col_names,
            working_df=working_df,
        )
        beu_deleted_rows = self._get_deleted_rows_for_backend()

        # Apply changes to working_df and check changes still in filters
        filters_changed, modified_df = self._check_for_filters_updates(modified_df)
        sorts_changed, modified_df = self._check_for_sorts_updates(
            modified_df=modified_df,
            added_rows=self.added_rows,
            edited_rows=self.edited_rows,
            deleted_rows=self.deleted_rows,
        )

        if sorts_changed or filters_changed:
            self.working_df = modified_df

        return frontend_models.BackendUpdates(
            added_rows=beu_added_rows,
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
            column_order=self._column_order,
            num_rows="dynamic",
        )
