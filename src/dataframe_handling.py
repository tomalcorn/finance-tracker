"""Module to handle dataframe loading and editing."""

import contextlib
import datetime
import re
import typing
import uuid

import gotrue
import pandas as pd
import streamlit as st
from pandas.api.types import (
    is_object_dtype,
)
from st_supabase_connection import SupabaseConnection
from streamlit_extras import stylable_container as sc

import config
import models
import utils

MAX_UNIQUE_VALUES = 20
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}.*")


class DFEButtons:
    """A class that provides Streamlit dataframe editing functionality with buttons."""

    def __init__(
        self,
        table_name: str,
        config: list[config.DFEColumnConfig],
        connection: SupabaseConnection,
        sorts: list[tuple[str, str | None]] | None = None,
        filters: dict[str, dict[str, typing.Any]] | None = None,
    ) -> None:
        """Initialize the DataframeEditor with a table name."""
        self.table_name = table_name
        self.config = config
        self.conn = connection
        self.table = connection.table(table_name)
        self.sorts = sorts
        self.filters = filters if filters is not None else {}

        # === Add button ===
        button_cols = st.columns((0.15, 0.1, 0.1, 0.6), border=False)
        with button_cols[0]:
            self.add_row_button = st.button(
                label="New",
                icon="➕",  # noqa: RUF001
                key=f"{self.table_name}_add_row_button",
            )
            if self.add_row_button:
                self.add_row_button_dialog()

        css_style_normal = """
        button {
            background-color: white;
            border: 1px solid #ccc;
            color: black;
        }
        """
        css_style_active = """
        button {
        background-color: rgba(212, 237, 218, 0.5); /* Light green background */
        border: 1px solid #ccc;
        color: black;
        }
        """
        # === Sort button ===
        with (
            button_cols[1],
            sc.stylable_container(
                key=f"{self.table_name}_sort_button_container",
                css_styles=css_style_active if not self.sorts else css_style_normal,
            ),
        ):
            self.sorting_button = st.button(
                label="",
                icon="↕️",
                key=f"{self.table_name}_sort_button",
            )
            if self.sorting_button:
                self.sorting_button_dialog()

        # === Filter button ===
        with (
            button_cols[2],
            sc.stylable_container(
                key=f"{self.table_name}_filter_button_container",
                css_styles=css_style_active if not self.filters else css_style_normal,
            ),
        ):
            self.filtering_button = st.button(
                label="",
                icon="🔍",
                key=f"{self.table_name}_filter_button",
            )
            if self.filtering_button:
                self.filtering_button_dialog()

    def get_unique_values(self, column_name: str) -> list[typing.Any]:
        """Get all unique values in a column by executing a select query."""
        vals = utils.get_column_values(self.conn, self.table_name, column_name)
        if not vals.empty:
            return vals.dropna().unique().tolist()
        return []

    def _get_min_max_values(self, column_name: str) -> tuple[float, float]:
        """Get min and max values for numeric columns using pandas."""
        column_data = utils.get_column_values(self.conn, self.table_name, column_name)
        min_value = column_data.min() if not column_data.empty else 0.0
        max_value = column_data.max() if not column_data.empty else 1.0
        return (min_value, max_value)

    @st.dialog("Add Row")
    def add_row_button_dialog(self) -> None:
        """Handle the add row button click event."""
        st.write(f"Add a new row to **{self.table_name}**")
        outputs = [
            column.input_widget(
                label=column.button_label or column.column,
                key=f"{self.table_name}_new_row_{column.column}",
                **column.input_kwargs,
            )
            for column in self.config
        ]
        options_unfilled = any(output is None or output == "" for output in outputs)
        submit_button = st.button(
            label="Submit",
            key=f"{self.table_name}_submit_new_row_button",
            disabled=options_unfilled,
        )
        if submit_button:
            new_row = {
                col.column: output
                for col, output in zip(self.config, outputs, strict=False)
            }
            # Insert ID and user ID
            new_row["id"] = str(uuid.uuid4())
            current_user: gotrue.types.User = st.session_state[
                models.SSKeys.CURRENT_USER
            ]
            new_row["user_id"] = current_user.id

            # Enforce unique constraint if specified
            unique_columns = [col.column for col in self.config if col.enforce_unique]
            utils.enforce_unique_cols(
                conn=self.conn,
                table_name=self.table_name,
                row=new_row,
                unique_columns=unique_columns,
            )

            # Handle foreign key mapping if provided
            for col in self.config:
                if col.foreign_key_mapping:
                    new_row[col.column] = col.foreign_key_mapping[new_row[col.column]]

            # convert date columns to ISO format, handle foreign keys
            for column_name, value in new_row.items():
                if isinstance(value, datetime.date):
                    new_row[column_name] = value.isoformat()
            self.table.upsert(new_row).execute()
            st.session_state.pop(f"{self.table_name}_working", None)
            st.rerun()

    @st.dialog("Sort Columns")
    def sorting_button_dialog(self) -> None:
        """Handle the sorting button click event."""
        st.write(f"Sort **{self.table_name}** by column")
        # Get sorts dict from session state or initialize
        sorts_dict = dict(self.sorts) if self.sorts else {}

        for col in self.config:
            sorts_dict[col.column] = st.selectbox(
                f"Sort by {col.button_label or col.column}",
                options=["asc", "desc", None],
                key=f"{self.table_name}_sort_{col.column}",
                index=["asc", "desc", None].index(sorts_dict.get(col.column))
                if col.column in sorts_dict
                else None,
            )
        submit_button = st.button(
            label="Submit Sort",
            key=f"{self.table_name}_submit_sort_button",
        )
        if submit_button:
            # Update sorts in session state with string values
            st.session_state[f"{self.table_name}_sorts"] = [
                (col, direction)
                for col, direction in sorts_dict.items()
                if direction is not None
            ]
            st.session_state.pop(f"{self.table_name}_working", None)
            st.rerun()

    @st.dialog("Filter Columns")
    def filtering_button_dialog(self) -> None:
        """Handle the filtering button click event."""
        st.write(f"Filter **{self.table_name}** by column")

        for col in self.config:
            if col.input_widget == st.date_input:
                self._handle_date_filter(col)
            elif col.input_widget == st.number_input:
                self._handle_number_filter(col)
            elif (unique_vals := self.get_unique_values(col.column)) and len(
                unique_vals,
            ) < MAX_UNIQUE_VALUES:
                self._handle_selectbox_filter(col, unique_vals)
            else:
                self._handle_generic_filter(col)

        submit_button = st.button(
            label="Submit Filter",
            key=f"{self.table_name}_submit_filter_button",
        )
        if submit_button:
            # Update filters in session state
            st.session_state[f"{self.table_name}_filters"] = {
                col: val for col, val in self.filters.items() if val is not None
            }
            st.session_state.pop(f"{self.table_name}_working", None)
            st.session_state.pop(f"{self.table_name}_current", None)
            st.rerun()

    def _handle_date_filter(self, col: config.DFEColumnConfig) -> None:
        """Handle filtering for date columns."""
        if self.filters.get(col.column) is not None:
            default_date_s = (
                self.filters[col.column]["gte"],
                self.filters[col.column]["lte"],
            )
        else:
            default_date_s = utils.get_start_and_end_of_month()

        selected_dates = st.date_input(
            f"Filter by {col.button_label or col.column}",
            value=default_date_s,
            key=f"{self.table_name}_filter_{col.column}",
        )

        if isinstance(selected_dates, tuple) and len(selected_dates) > 1:
            self.filters[col.column] = {
                "gte": selected_dates[0].isoformat(),
                "lte": selected_dates[1].isoformat(),
            }
        elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
            self.filters[col.column] = {
                "gte": selected_dates[0].isoformat(),
                "lte": selected_dates[0].isoformat(),
            }
        else:
            self.filters[col.column] = {}

    def _handle_number_filter(self, col: config.DFEColumnConfig) -> None:
        """Handle filtering for numeric columns."""
        if col.column in self.filters:
            min_value = self.filters[col.column]["gte"]
            max_value = self.filters[col.column]["lte"]
        else:
            min_value, max_value = self._get_min_max_values(col.column)
        if min_value == max_value:
            self.filters.pop(col.column, None)
            return  # No need to show slider if min and max are the same
        step = (max_value - min_value) / 100
        selected_values = st.slider(
            f"Filter by {col.button_label or col.column}",
            min_value=min_value,
            max_value=max_value,
            value=(min_value, max_value),
            step=step,
            key=f"{self.table_name}_filter_{col.column}",
        )
        if selected_values == (min_value, max_value):
            self.filters.pop(col.column, None)
        else:
            self.filters[col.column] = {
                "gte": selected_values[0],
                "lte": selected_values[1],
            }

    def _handle_selectbox_filter(
        self,
        col: config.DFEColumnConfig,
        unique_vals: list[typing.Any],
    ) -> None:
        """Handle filtering using a selectbox for columns with few unique values."""
        selected_values = st.multiselect(
            f"Filter by {col.button_label or col.column}",
            options=unique_vals,
            default=self.filters.get(col.column, []),
            key=f"{self.table_name}_filter_{col.column}",
        )
        self.filters[col.column] = {"in": selected_values} if selected_values else {}

    def _handle_generic_filter(self, col: config.DFEColumnConfig) -> None:
        """Handle generic filtering for other column types."""
        user_text_input = st.text_input(
            f"Filter by {col.button_label or col.column}",
            value=self.filters.get(col.column, ""),
            key=f"{self.table_name}_filter_{col.column}",
        )
        self.filters[col.column] = (
            {"contains": user_text_input} if user_text_input else {}
        )


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_name: str,
        sample_data: pd.DataFrame,
        connection: SupabaseConnection,
        config: list[config.DFEColumnConfig],
        column_order: list[str],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.conn = connection
        self.table = self.conn.table(table_name)
        self.config = config

        self._initialize_column_settings(config, column_order)
        self._initialize_session_state(sample_data)

        # Set up buttons
        DFEButtons(
            table_name=self.table_name,
            config=self.config,
            connection=self.conn,
            sorts=self.sorts,
            filters=self.filters,
        )

    def _initialize_column_settings(
        self,
        config: list[config.DFEColumnConfig],
        column_order: list[str],
    ) -> None:
        """Initialize column configuration and order."""
        self.column_config = {col.column: col.column_config for col in config}
        self.column_order = column_order

        # Retrieve sorting from session state or config
        if f"{self.table_name}_sorts" in st.session_state:
            self.sorts = st.session_state[f"{self.table_name}_sorts"]
        else:
            self.sorts = [(col.column, col.sorting) for col in config if col.sorting]

        # Retrieve filtering from session state or config
        if f"{self.table_name}_filters" in st.session_state:
            self.filters = st.session_state[f"{self.table_name}_filters"]
        else:
            self.filters = {
                col.column: col.filtering for col in config if col.filtering is not None
            }

    def _initialize_session_state(self, sample_data: pd.DataFrame) -> None:
        """Initialize session state variables."""
        # Load and store original data in working and current session states variables
        if f"{self.table_name}_working" not in st.session_state:
            original_data = pd.DataFrame(
                utils.get_original_data(
                    _conn=self.conn,
                    table_name=self.table_name,
                    query_string="*",
                    filters=self.filters,
                ),
            )
            # Handle foreign key mapping if provided
            for col in self.config:
                if col.foreign_key_mapping:
                    original_data[col.column] = original_data[col.column].map(
                        col.foreign_key_mapping,
                    )
            working_df = self._convert_cols_to_datetime(
                original_data if not original_data.empty else sample_data,
            )
            if self.sorts:
                working_df = self.sort_columns(working_df)
            st.session_state[f"{self.table_name}_working"] = working_df

        if f"{self.table_name}_current" not in st.session_state:
            st.session_state[f"{self.table_name}_current"] = st.session_state.get(
                f"{self.table_name}_working",
            )

        # Set up backend updates session state dict
        if f"{self.table_name}_backend_updates" not in st.session_state:
            st.session_state[f"{self.table_name}_backend_updates"] = {
                "added_rows": [],
                "edited_rows": {},
                "deleted_rows": [],
            }

        # Set up added row ids session state
        if f"{self.table_name}_row_ids" not in st.session_state:
            st.session_state[f"{self.table_name}_row_ids"] = []

        # Set up previous added rows session state
        if f"{self.table_name}_prev_added_rows" not in st.session_state:
            st.session_state[f"{self.table_name}_prev_added_rows"] = []

    def _convert_cols_to_datetime(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """Try to convert columns to datetime."""
        for col in dataframe.columns:
            if is_object_dtype(dataframe[col]):
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
        _self,  # noqa: N805
        working_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Sort the original dataframe by a list of column names."""
        sorted_df = working_df.copy()
        if _self.sorts is not None:
            for col, direction in _self.sorts:
                ascending = direction.lower() == "asc"
                sorted_df = sorted_df.sort_values(by=col, ascending=ascending)
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
        unique_cols = [col.column for col in self.config if col.enforce_unique]

        # === Deal with added rows ===
        added_rows = editor_state["added_rows"]
        row_ids: list = st.session_state[f"{self.table_name}_row_ids"]
        backend_added_rows: list = st.session_state[
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
        working_df: pd.DataFrame = st.session_state[f"{self.table_name}_working"]
        return st.data_editor(
            working_df,
            key=self.table_name,
            column_config=self.column_config,
            column_order=self.column_order,
            num_rows="dynamic",
            on_change=self.sync,
        )

    def write_changes_to_backend(
        self,
        modified_df: pd.DataFrame,
    ) -> None:
        """Write changes from modified_df to DB."""
        backend_updates = st.session_state[f"{self.table_name}_backend_updates"]
        added_rows: list = backend_updates["added_rows"]
        edited_rows: dict = backend_updates["edited_rows"]
        deleted_rows: list = backend_updates["deleted_rows"]

        # map foreign keys if provided
        for col in self.config:
            if col.foreign_key_mapping:
                for row in added_rows:
                    row[col.column] = col.foreign_key_mapping.get(
                        row[col.column],
                        row[col.column],
                    )
                for changes in edited_rows.values():
                    if col.column in changes:
                        changes[col.column] = col.foreign_key_mapping.get(
                            changes[col.column],
                            changes[col.column],
                        )

        # === Deal with deleted rows ===
        current_df: pd.DataFrame = st.session_state[f"{self.table_name}_current"]
        deleted_ids = list(set(current_df["id"]) - set(modified_df["id"]))
        deleted_rows.extend(deleted_ids)

        # Add user_id to all rows
        current_user: gotrue.types.User = st.session_state[models.SSKeys.CURRENT_USER]
        for row in added_rows:
            row["user_id"] = current_user.id
        for changes in edited_rows.values():
            changes["user_id"] = current_user.id
        for row in deleted_rows:
            row["user_id"] = current_user.id

        if added_rows:
            self.table.upsert(added_rows).execute()

        if edited_rows:
            for row_id, update_data in edited_rows.items():
                self.table.update(update_data).eq("id", row_id).execute()

        if deleted_rows:
            self.table.delete().in_("id", deleted_rows).execute()
            deleted_rows = []

        st.session_state[f"{self.table_name}_current"] = modified_df.copy()
