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

    def clear_working_df(self) -> None:
        """Clear the working dataframe from session state."""
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        if working_df_key in st.session_state:
            del st.session_state[working_df_key]

    @property
    def original_df(self) -> pd.DataFrame | None:
        """Get the original dataframe from session state."""
        original_df_key = f"{self.table_name}_{constants.SSKeys.ORIGINAL_DF}"
        return st.session_state.get(original_df_key, None)

    @original_df.setter
    def original_df(self, df: pd.DataFrame) -> None:
        """Set the original dataframe in session state."""
        original_df_key = f"{self.table_name}_{constants.SSKeys.ORIGINAL_DF}"
        st.session_state[original_df_key] = df

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

        # Load current data from database
        current_df = pd.DataFrame(
            data_client.get_data(
                table_name=self.table_name,
                query_string="*",
                configs=self.configs,
            ),
        )

        # Initialize original_df on first load
        if self.original_df is None:
            self.original_df = current_df

        # If database data has changed, reset working state
        elif not current_df.equals(self.original_df):
            self.clear_working_df()
            self.original_df = current_df

        # Initialize working_df if needed
        if self.working_df is None:
            source_df = (
                self.original_df
                if (self.original_df and not self.original_df.empty)
                else sample_data
            )
            working_df = self._convert_cols_to_datetime(source_df)
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
        added_rows: dict[str, typing.Any] | None = None,
        edited_rows: dict[str, dict[str, typing.Any]] | None = None,
        deleted_rows: list[int] | None = None,
    ) -> bool:
        """Check editor_state to see if changes made to sorts columns."""
        if deleted_rows:
            return True

        sorts_changed = False
        for config in self.configs:
            if config.sorting is not None:
                col = config.column_name

                if edited_rows:
                    for changes in edited_rows.values():
                        if col in changes:
                            sorts_changed = True
                            break

                if not sorts_changed and added_rows:
                    for row in added_rows:
                        if col in row:
                            sorts_changed = True
                            break
        return sorts_changed

    def sort_columns(
        self,
        working_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Sort the original dataframe by a list of column names."""
        sorted_df = working_df.copy()
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
        unique_columns: list[str],
    ) -> None:
        """Process a single row to enforce unique constraints."""
        for col in unique_columns:
            if col in row:
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

    def sync(
        self,
        working_df: pd.DataFrame,
        modified_df: pd.DataFrame,
    ) -> frontend_models.BackendUpdates:
        """Sync the edited dataframe with the Supabase table."""
        # Get the editor state and working dataframe
        editor_state = st.session_state[self.table_name]
        unique_cols = [col.column_name for col in self.configs if col.enforce_unique]

        # === Deal with added rows ===
        added_rows_key = constants.SSKeys.ADDED_ROWS
        beu_added_rows: list[dict[str, typing.Any]] = []
        added_rows: list[dict[str, typing.Any]] = editor_state[added_rows_key]

        row_ids_key = f"{self.table_name}_{constants.SSKeys.ROW_IDS}"
        row_ids: list[str] = st.session_state[row_ids_key]

        prev_added_rows_key = f"{self.table_name}_{constants.SSKeys.PREV_ADDED_ROWS}"
        prev_added_rows: list[dict[str, typing.Any]] = st.session_state[
            prev_added_rows_key
        ]

        # Deal with deleted added_rows
        if len(added_rows) < len(row_ids):
            deleted_added_indices = [
                i for i, row in enumerate(prev_added_rows) if row not in added_rows
            ]
            for idx in sorted(deleted_added_indices, reverse=True):
                del row_ids[idx]
        st.session_state[prev_added_rows_key] = added_rows

        # Assign IDs to added rows: reuse IDs from row_ids if available
        for i, row in enumerate(added_rows):
            self._enforce_unique_cols(
                row=row,
                unique_columns=unique_cols,
            )
            if i < len(row_ids):
                row["id"] = row_ids[i]
            elif "id" not in row or not row["id"]:
                row["id"] = str(uuid.uuid4())
                beu_added_rows.append(row)

        # === Deal with edited rows ===
        edited_rows_key = constants.SSKeys.EDITED_ROWS
        edited_rows: dict[str, dict[str, typing.Any]] = editor_state[edited_rows_key]
        beu_edited_rows: dict[str, dict[str, typing.Any]] = {}
        for row_idx, changes in edited_rows.items():
            self._enforce_unique_cols(
                row=changes,
                unique_columns=unique_cols,
            )
            row_id = working_df.iloc[row_idx]["id"]
            beu_edited_rows[row_id] = changes

        # === Deal with deleted rows ===
        deleted_rows_key = constants.SSKeys.DELETED_ROWS
        deleted_rows: list[int] = editor_state[deleted_rows_key]
        beu_deleted_rows: list[str] = []
        for row_idx in deleted_rows:
            row_id = working_df.iloc[row_idx]["id"]
            beu_deleted_rows.append(row_id)

        # Apply changes to working_df and check changes still in filters
        filters_changed, modified_df = self._check_for_filters_updates(modified_df)
        sorts_changed = any(
            col.sorting for col in self.configs
        ) and self._check_for_sorts_updates(
            added_rows=editor_state[constants.SSKeys.ADDED_ROWS],
            edited_rows=editor_state[constants.SSKeys.EDITED_ROWS],
            deleted_rows=editor_state[constants.SSKeys.DELETED_ROWS],
        )
        if sorts_changed:
            modified_df = self.sort_columns(modified_df)
        if sorts_changed or filters_changed:
            st.session_state[f"{self.table_name}_{constants.SSKeys.WORKING_DF}"] = (
                modified_df
            )

        return frontend_models.BackendUpdates(
            added_rows=beu_added_rows,
            edited_rows=beu_edited_rows,
            deleted_rows=beu_deleted_rows,
        )

    def render(self) -> pd.DataFrame:
        """Render the dataframe editor with the original dataframe."""
        # Get working dataframe from session state
        if self.working_df is None:
            msg = "Working dataframe is not initialized."
            raise ValueError(msg)
        return st.data_editor(
            self.working_df,
            key=self.table_name,
            column_config=self._column_config,
            column_order=self._column_order,
            num_rows="dynamic",
        )
