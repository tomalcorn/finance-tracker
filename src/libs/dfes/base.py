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
        sample_data: pd.DataFrame,
        configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.configs = configs

        self._initialize_session_state(sample_data)

    def _initialize_session_state(self, sample_data: pd.DataFrame) -> None:
        """Initialize session state variables."""
        # Load and store original data in working and current session states variables
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        if working_df_key not in st.session_state:
            original_data = pd.DataFrame(
                data_client.get_data(
                    table_name=self.table_name,
                    query_string="*",
                    configs=self.configs,
                ),
            )
            working_df = self._convert_cols_to_datetime(
                original_data if not original_data.empty else sample_data,
            )
            st.session_state[working_df_key] = working_df

        current_df_key = f"{self.table_name}_{constants.SSKeys.CURRENT_DF}"
        if current_df_key not in st.session_state:
            st.session_state[current_df_key] = st.session_state.get(
                working_df_key,
            )

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
        """Check working_df to see if changes fall outside current filters.

        Args:
            working_df: The DataFrame to check against filters

        Returns:
            A tuple of (bool, pd.DataFrame) where the bool indicates if the DataFrame
            changed due to filtering, and the DataFrame is the possibly modified result

        """
        query_conditions = []
        for col, condition in self.filters.items():
            if isinstance(condition, dict):
                for op in condition:
                    if op == "gte":
                        query_conditions.append(f"{col} >= @value_{col}_{op}")
                    elif op == "lte":
                        query_conditions.append(f"{col} <= @value_{col}_{op}")
                    elif op == "eq":
                        query_conditions.append(f"{col} == @value_{col}_{op}")
                    else:
                        query_conditions.append(f"{col} == @value_{col}_eq")

        query_string = " and ".join(query_conditions)
        query_params = {
            f"value_{col}_{op}": pd.to_datetime(value)
            if op in {"gte", "lte"}
            else value
            for col, condition in self.filters.items()
            for op, value in (
                condition.items()
                if isinstance(condition, dict)
                else [("eq", condition)]
            )
        }

        filtered_df = working_df.query(query_string, local_dict=query_params)

        # Check if any rows were filtered out
        if len(filtered_df) != len(working_df):
            return True, filtered_df.reset_index(drop=True)

        return False, working_df

    def _check_for_sorts_updates(
        self,
        editor_state: dict[str, typing.Any],
    ) -> bool:
        """Check editor_state to see if changes made to sorts columns."""
        sorts_changed = False
        if self.sorts:
            sort_columns = [col for col, _ in self.sorts]

            # Check for edits in sorted columns
            if editor_state.get("edited_rows"):
                for changes in editor_state["edited_rows"].values():
                    if any(col in sort_columns for col in changes):
                        sorts_changed = True
                        break

            # Check for additions that may affect sorted columns
            if not sorts_changed and editor_state.get("added_rows"):
                for new_row in editor_state["added_rows"]:
                    if any(col in sort_columns for col in new_row):
                        sorts_changed = True
                        break

            # Check for deletions
            if not sorts_changed and editor_state.get("deleted_rows"):
                sorts_changed = True  # Deletion affects sorting indirectly
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

    def _add_rows(
        self,
        working_df: pd.DataFrame,
        added_rows: list[dict[str, typing.Any]],
    ) -> pd.DataFrame:
        """Add any rows in the DFE to backend and update working_df."""
        for new_row_data in added_rows:
            new_row_df = pd.DataFrame([new_row_data])
            new_row_df_conv = self._convert_cols_to_datetime(new_row_df)

            # Append the new row to the working dataframe
            working_df = pd.concat([working_df, new_row_df_conv], ignore_index=True)

        return working_df

    def _edit_rows(
        self,
        working_df: pd.DataFrame,
        edited_rows: dict[int, typing.Any],
    ) -> pd.DataFrame:
        """Edit any rows in the DFE in backend and update working_df."""
        for row_idx, changes in edited_rows.items():
            if row_idx >= len(working_df) or "id" not in working_df.columns:
                continue
            row_id = working_df.iloc[row_idx]["id"]

            # Build update data
            update_data = {}
            for col, value in changes.items():
                if col == "payment_date" and value is not None:
                    converted_value = pd.to_datetime(value)
                    update_data[col] = converted_value.isoformat()
                else:
                    update_data[col] = value

                working_df.loc[working_df["id"] == row_id, col] = (
                    converted_value
                    if col == "payment_date" and value is not None
                    else value
                )

        return working_df

    def _delete_rows(
        self,
        working_df: pd.DataFrame,
        deleted_rows: list[int],
    ) -> pd.DataFrame:
        """Remove any rows from the backend and update working_df."""
        # Sort in reverse order to maintain correct indexes during deletion
        deletions_for_the_backend = []
        for row_idx in sorted(deleted_rows, reverse=True):
            if row_idx >= len(working_df) or "id" not in working_df.columns:
                continue  # Skip if row doesn't exist or no ID column

            row_id = working_df.iloc[row_idx]["id"]
            deletions_for_the_backend.append(row_id)

            # Remove from working dataframe
            working_df = working_df[working_df["id"] != row_id].reset_index(drop=True)

        return working_df

    def _apply_changes_to_working_df(
        self,
        editor_state: dict[str, typing.Any],
        working_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply changes from editor state to working_df."""
        if editor_state.get("added_rows"):
            added_rows = editor_state["added_rows"]
            working_df = self._add_rows(working_df, added_rows)

        if editor_state.get("edited_rows"):
            edited_rows = editor_state["edited_rows"]
            working_df = self._edit_rows(working_df, edited_rows)

        if editor_state.get("deleted_rows"):
            deleted_rows = editor_state["deleted_rows"]
            working_df = self._delete_rows(working_df, deleted_rows)

        return working_df

    def sync(self) -> None:
        """Sync the edited dataframe with the Supabase table."""
        # Get the editor state and working dataframe
        editor_state = st.session_state[self.table_name]
        working_df: pd.DataFrame = st.session_state[f"{self.table_name}_working"].copy()
        working_df = self._apply_changes_to_working_df(editor_state, working_df)
        unique_cols = [col.column_name for col in self.configs if col.enforce_unique]

        # === Deal with added rows ===
        added_rows = editor_state["added_rows"]
        row_ids: list[int] = st.session_state[f"{self.table_name}_row_ids"]
        backend_added_rows: list[int] = st.session_state[
            f"{self.table_name}_backend_updates"
        ]["added_rows"]
        # Deal with deleted added_rows
        if len(added_rows) < len(row_ids):
            prev_added_rows = st.session_state[f"{self.table_name}_prev_added_rows"]
            deleted_added_indices = [
                i for i, row in enumerate(prev_added_rows) if row not in added_rows
            ]
            for idx in sorted(deleted_added_indices, reverse=True):
                del row_ids[idx]
        st.session_state[f"{self.table_name}_prev_added_rows"] = added_rows.copy()
        # Assign IDs to added rows: reuse IDs from row_ids if available
        for i, row in enumerate(added_rows):
            utils.enforce_unique_cols(
                conn=self.conn,
                table_name=self.table_name,
                row=row,
                unique_columns=unique_cols,
            )
            if i < len(row_ids):
                row["id"] = row_ids[i]
            elif "id" not in row or not row["id"]:
                row["id"] = str(uuid.uuid4())
                backend_row = row.copy()
                backend_added_rows.append(backend_row)

        # === Deal with edited rows ===
        edited_rows = editor_state["edited_rows"]
        backend_edited_rows: dict[str, typing.Any] = st.session_state[
            f"{self.table_name}_backend_updates"
        ]["edited_rows"]
        for row_idx, changes in edited_rows.items():
            utils.enforce_unique_cols(
                conn=self.conn,
                table_name=self.table_name,
                row=changes,
                unique_columns=unique_cols,
            )
            row_id = working_df.iloc[row_idx]["id"]
            backend_edited_rows[row_id] = changes

        # Apply changes to working_df and check changes still in filters
        filters_changed, working_df = self._check_for_filters_updates(working_df)
        sorts_changed = self.sorts and self._check_for_sorts_updates(editor_state)
        if sorts_changed:
            working_df = self.sort_columns(working_df)
        if sorts_changed or filters_changed:
            st.session_state[f"{self.table_name}_working"] = working_df

    def render(self) -> pd.DataFrame:
        """Render the dataframe editor with the original dataframe."""
        # Get working dataframe from session state
        working_df_key = f"{self.table_name}_{constants.SSKeys.WORKING_DF}"
        working_df: pd.DataFrame = st.session_state[working_df_key]
        return st.data_editor(
            working_df,
            key=self.table_name,
            column_config=self.column_config,
            column_order=self.column_order,
            num_rows="dynamic",
            on_change=self.sync,
        )
