"""Module to handle dataframe loading and editing."""

import contextlib
import datetime
import logging
import re
import time
import typing
import uuid

import pandas as pd
import pydantic
import streamlit as st
import streamlit.elements.lib.column_types as st_column_types
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from st_supabase_connection import SupabaseConnection
from streamlit_extras import stylable_container as sc

MAX_UNIQUE_VALUES = 20
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}.*")


class DFEWithFilters:
    """A class that provides Streamlit dataframe editing functionality.

    Filtering, search, and CRUD operations that maintain the original dataframe
    structure.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        session_key: str = "dfa",
        column_config: dict | None = None,
        column_order: list[str] | None = None,
    ) -> None:
        """Initialize the DataframeEditor with a pandas DataFrame.

        Args:
            df: The pandas DataFrame to edit
            session_key: The key to use for storing the DataFrame in session_state
            column_config: Streamlit column configuration dictionary
            column_order: Order of columns to display

        """
        # Initialize the dataframe in session state if not already present
        if session_key not in st.session_state:
            st.session_state[session_key] = df.copy()

        self.session_key = session_key
        self.column_config = column_config
        self.column_order = column_order

        # Create a unique key for the editor
        self.table_name = f"{session_key}_editor"

        # Track newly added rows to ensure they're visible even with filtering
        if f"{session_key}_newly_added_row" not in st.session_state:
            st.session_state[f"{session_key}_newly_added_row"] = None

    @property
    def df(self) -> pd.DataFrame:
        """Get the current dataframe from session state."""
        return st.session_state[self.session_key]

    def active_df(self) -> pd.DataFrame:
        """Return filtered dataframe with reset index to avoid UI confusion."""
        # Handle NaN values by filling them with False
        active_col = self.df["Active"].fillna(value=False)
        filtered_df = self.df[active_col].copy()
        # Store original index in a hidden column for reference
        filtered_df["_original_index"] = filtered_df.index
        # Reset the index for the UI display
        return filtered_df.reset_index(drop=True)

    def get_original_index(self, row: int) -> int:
        """Get the original index from the hidden column."""
        return self.active_df().iloc[row]["_original_index"]

    def commit_to_db(self) -> None:
        """Commit changes from the data editor to the session state dataframe."""
        self._commit_edited_rows()
        self._commit_added_rows()
        self._commit_deleted_rows()

    def _commit_edited_rows(self) -> None:
        """Handle edited rows and update the dataframe."""
        if "edited_rows" in st.session_state[self.table_name]:
            for row in st.session_state[self.table_name]["edited_rows"]:
                original_idx = self.get_original_index(int(row))
                for key, value in st.session_state[self.table_name]["edited_rows"][
                    row
                ].items():
                    if key != "_original_index":  # Don't modify our reference column
                        self.df.loc[original_idx, key] = value

    def _commit_added_rows(self) -> None:
        """Handle added rows and append them to the dataframe."""
        if "added_rows" in st.session_state[self.table_name]:
            for row in st.session_state[self.table_name]["added_rows"]:
                new_row: dict = {}
                for col in self.df.columns:
                    if col == "Active":
                        new_row[col] = True
                    elif is_numeric_dtype(self.df[col]):
                        new_row[col] = 0
                    elif is_datetime64_any_dtype(self.df[col]):
                        new_row[col] = pd.Timestamp.now()
                    elif is_object_dtype(self.df[col]):
                        new_row[col] = ""
                    else:
                        new_row[col] = None

                new_row["Active"] = True

                new_row.update(
                    {
                        key: value
                        for key, value in row.items()
                        if key != "_original_index"
                    },
                )

                st.session_state[self.session_key] = pd.concat(
                    [self.df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                st.session_state[f"{self.session_key}_newly_added_row"] = new_row

    def _commit_deleted_rows(self) -> None:
        """Handle deleted rows and remove them from the dataframe."""
        if "deleted_rows" in st.session_state[self.table_name]:
            indices_to_delete = []
            for row in st.session_state[self.table_name]["deleted_rows"]:
                original_idx = self.get_original_index(int(row))
                indices_to_delete.append(original_idx)

            if indices_to_delete:
                st.session_state[self.session_key] = self.df.drop(
                    indices_to_delete,
                ).reset_index(
                    drop=True,
                )

    def filter_dataframe(self) -> None:
        """Filter the dataframe based on filters from the multiselect."""
        # Reset all active states first
        self.df["Active"] = False

        # Get filter mask from UI components
        mask = self.get_filter_mask()

        # Also mark true if row matches newly added row
        if st.session_state[f"{self.session_key}_newly_added_row"] is not None:
            new_row = st.session_state[f"{self.session_key}_newly_added_row"]
            # Compare only the relevant columns for matching
            match_new_row = pd.Series(data=True, index=self.df.index)
            for col in self.df.columns:
                if col in new_row and col != "Active":
                    col_match = self.df[col] == new_row[col]
                    match_new_row &= col_match

            mask = mask | match_new_row

        self.df.loc[mask, "Active"] = True

    def get_filter_mask(self) -> pd.Series:
        """Display filter options for the dataframe. Return a mask for filtering."""
        # Initialize mask with all True values
        mask = pd.Series(data=True, index=self.df.index)

        for col in self.df.columns:
            if is_object_dtype(self.df[col]):
                with contextlib.suppress(Exception):
                    self.df[col] = pd.to_datetime(self.df[col])

            if is_datetime64_any_dtype(self.df[col]):
                self.df[col] = self.df[col].dt.tz_localize(None)

        modification_container = st.expander(label="Filter Options")

        with modification_container:
            to_filter_columns = st.multiselect("Filter dataframe on", self.df.columns)

            for column in to_filter_columns:
                left, right = st.columns((1, 20))
                # Treat columns with < 10 unique values as categorical
                # - no but if you want to then ( or df[column].nunique() < 10)
                if (
                    is_object_dtype(self.df[column])
                    and len(self.df[column].unique()) < MAX_UNIQUE_VALUES
                ):
                    user_cat_input = right.multiselect(
                        f"Values for {column}",
                        self.df[column].unique(),
                        default=list(self.df[column].unique()),
                    )
                    mask &= self.df[column].isin(user_cat_input)

                elif is_numeric_dtype(self.df[column]):
                    _min = float(self.df[column].min())
                    _max = float(self.df[column].max())
                    step = (_max - _min) / 100
                    user_num_input = right.slider(
                        f"Values for {column}",
                        min_value=_min,
                        max_value=_max,
                        value=(_min, _max),
                        step=step,
                    )
                    mask &= self.df[column].between(*user_num_input)

                elif is_datetime64_any_dtype(self.df[column]):
                    user_date_input = right.date_input(
                        f"Values for {column}",
                        value=(
                            self.df[column].min(),
                            self.df[column].max(),
                        ),
                    )
                    if len(user_date_input) == 2:  # noqa: PLR2004
                        user_date_input = tuple(map(pd.to_datetime, user_date_input))  # type: ignore[assignment]
                        start_date, end_date = user_date_input
                        mask &= self.df[column].between(start_date, end_date)

                else:
                    user_text_input = right.text_input(
                        f"Substring or regex in {column}",
                    )
                    if user_text_input:
                        mask &= (
                            self.df[column].astype(str).str.contains(user_text_input)
                        )

        return mask

    def render(self) -> pd.DataFrame:
        """Render the dataframe editor with filter functionality.

        Returns:
            The edited dataframe

        """
        # Filter dataframe based on UI filters
        self.filter_dataframe()

        # Prepare column config if not provided
        if self.column_config is None:
            self.column_config = {}

        # Display data editor with dynamic rows
        return st.data_editor(
            self.active_df(),
            column_order=self.column_order,
            column_config=self.column_config,
            num_rows="dynamic",
            key=self.table_name,
            on_change=self.commit_to_db,
        )


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame Editor."""

    column: str
    column_config: st_column_types.ColumnConfig
    button_label: str | None = None
    input_widget: typing.Any
    input_kwargs: dict = {}
    sorting: typing.Literal["asc", "desc", None] = None
    filtering: str | dict[str, str] | None = None


class DFEButtons:
    """A class that provides Streamlit dataframe editing functionality with buttons."""

    def __init__(
        self,
        table_name: str,
        config: list[DFEColumnConfig],
        table: SupabaseConnection,
        sorts: list[tuple[str, str | None]] | None = None,
        filters: dict[str, str | dict[str, str]] | None = None,
    ) -> None:
        """Initialize the DataframeEditor with a table name."""
        self.table_name = table_name
        self.config = config
        self.table = table
        self.sorts = sorts
        self.filters = filters

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
        """Get all unique values in a column from Supabase."""
        query = self.table.select(column_name).distinct(column_name).execute()
        return [row[column_name] for row in query.data]

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
            new_row["id"] = str(uuid.uuid4())
            # convert date columns to ISO format
            for col, value in new_row.items():
                if isinstance(value, datetime.date):
                    new_row[col] = value.isoformat()
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
        # Get filters dict from session state or initialize
        filters_dict = st.session_state.get(f"{self.table_name}_filters", {})

        submit_button = st.button(
            label="Submit Filter",
            key=f"{self.table_name}_submit_filter_button",
        )
        if submit_button:
            # Update filters in session state
            st.session_state[f"{self.table_name}_filters"] = {
                col: val for col, val in filters_dict.items() if val is not None
            }
            st.session_state.pop(f"{self.table_name}_working", None)
            st.rerun()


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_name: str,
        sample_data: pd.DataFrame,
        connection: SupabaseConnection,
        config: list[DFEColumnConfig],
        column_order: list[str],
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.conn = connection
        self.table = self.conn.table(table_name)
        self.config = config

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

        # Load and store original data in working and current session states variables
        if f"{self.table_name}_working" not in st.session_state:
            original_data = self._get_original_data(filters=self.filters)
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

        # Set up buttons
        DFEButtons(
            table_name=self.table_name,
            config=self.config,
            table=self.table,
            sorts=self.sorts,
        )

    def _get_original_data(
        self,
        filters: dict[str, str | dict[str, str]],
    ) -> pd.DataFrame:
        """Fetch original dataframe from backend."""
        query = self.table.select("*")
        for col, condition in filters.items():
            if isinstance(condition, dict):
                for op, value in condition.items():
                    query = query.filter(col, op, value)
            else:
                query = query.eq(col, condition)
        return pd.DataFrame(query.execute().data)

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
                if any(DATE_PATTERN.match(val) for val in sample_values):
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
        start = time.time()
        editor_state = st.session_state[self.table_name]
        working_df: pd.DataFrame = st.session_state[f"{self.table_name}_working"].copy()

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
            row_id = working_df.iloc[row_idx]["id"]
            backend_edited_rows[row_id] = changes

        # First apply changes to working_df copy to check changes fall outside filter
        # Return (bool, pd.DataFrame) tuple
        # If true, override working_df with the copy
        # Pass modified or unmodified working_df to sort method if necessary

        # Apply changes to working_df and check changes still in filters
        working_df = self._apply_changes_to_working_df(editor_state, working_df)
        filters_changed, working_df = self._check_for_filters_updates(working_df)
        sorts_changed = self.sorts and self._check_for_sorts_updates(editor_state)
        if sorts_changed:
            working_df = self.sort_columns(working_df)
        if sorts_changed or filters_changed:
            st.session_state[f"{self.table_name}_working"] = working_df

        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).info("Sync took %.4f seconds", time.time() - start)

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

        # === Deal with deleted rows ===
        current_df: pd.DataFrame = st.session_state[f"{self.table_name}_current"]
        deleted_ids = list(set(current_df["id"]) - set(modified_df["id"]))
        deleted_rows.extend(deleted_ids)

        if added_rows:
            self.table.upsert(added_rows).execute()

        if edited_rows:
            for row_id, update_data in edited_rows.items():
                self.table.update(update_data).eq("id", row_id).execute()

        if deleted_rows:
            self.table.delete().in_("id", deleted_rows).execute()
            deleted_rows = []

        st.session_state[f"{self.table_name}_current"] = modified_df.copy()
