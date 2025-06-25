"""Module to handle dataframe loading and editing."""

import contextlib
import json
import typing

import pandas as pd
import streamlit as st
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from st_supabase_connection import SupabaseConnection

MAX_UNIQUE_VALUES = 20


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
        self.editor_key = f"{session_key}_editor"

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
        if "edited_rows" in st.session_state[self.editor_key]:
            for row in st.session_state[self.editor_key]["edited_rows"]:
                original_idx = self.get_original_index(int(row))
                for key, value in st.session_state[self.editor_key]["edited_rows"][row].items():
                    if key != "_original_index":  # Don't modify our reference column
                        self.df.loc[original_idx, key] = value

    def _commit_added_rows(self) -> None:
        """Handle added rows and append them to the dataframe."""
        if "added_rows" in st.session_state[self.editor_key]:
            for row in st.session_state[self.editor_key]["added_rows"]:
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
                    {key: value for key, value in row.items() if key != "_original_index"},
                )

                st.session_state[self.session_key] = pd.concat(
                    [self.df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                st.session_state[f"{self.session_key}_newly_added_row"] = new_row

    def _commit_deleted_rows(self) -> None:
        """Handle deleted rows and remove them from the dataframe."""
        if "deleted_rows" in st.session_state[self.editor_key]:
            indices_to_delete = []
            for row in st.session_state[self.editor_key]["deleted_rows"]:
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
                        mask &= self.df[column].astype(str).str.contains(user_text_input)

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
            key=self.editor_key,
            on_change=self.commit_to_db,
        )


class DFE:
    """A class that provides Streamlit dataframe editing functionality."""

    def __init__(
        self,
        table_name: str,
        editor_key: str,
        connection: SupabaseConnection,
        column_config: dict | None = None,
        column_order: list[str] | None = None,
    ) -> None:
        """Initialize the DataframeEditor with a Supabase table."""
        self.table_name = table_name
        self.editor_key = editor_key
        self.conn = connection
        self.table = self.conn.table(table_name)
        self.column_config = column_config
        self.column_order = column_order

        # Load and store original data
        self.original_df = pd.DataFrame(self.table.select("*").execute().data)
        self.original_df["payment_date"] = pd.to_datetime(
            self.original_df["payment_date"],
        )
        st.session_state[f"{self.editor_key}_original"] = self.original_df

    def _add_rows(self, added_rows: list[dict[str, typing.Any]]) -> None:
        """Add any rows in the DFE to backend."""
        for new_row_data in added_rows:
            if "payment_date" in new_row_data and new_row_data["payment_date"] is not None:
                new_row_data["payment_date"] = pd.to_datetime(
                    new_row_data["payment_date"],
                )

            # Remove the id column if present (let DB generate it)
            if "id" in new_row_data:
                new_row_data.pop("id")

            self.table.insert(new_row_data).execute()

    def _edit_rows(
        self,
        edited_rows: dict[str, typing.Any],
        working_df: pd.DataFrame,
    ) -> None:
        """Edit any rows in the DFE in backend."""
        for row_idx, changes in edited_rows.items():
            for col, value in changes.items():
                if col == "payment_date" and value is not None:
                    converted_value = pd.to_datetime(value)
                else:
                    converted_value = value
                working_df.loc[row_idx, col] = converted_value

        # Update changed rows in Supabase
        for row_idx in edited_rows:
            row_id = working_df.loc[row_idx, "id"]
            row_data_json = (
                working_df.loc[row_idx]
                .drop("id")
                .to_json(
                    date_format="iso",
                    date_unit="s",
                )
            )
            row_data = json.loads(row_data_json)
            self.table.update(row_data).eq("id", row_id).execute()

    def _delete_rows(
        self,
        deleted_rows: list[int],
        original_df: pd.DataFrame,
    ) -> None:
        """Remove any rows from the backend."""
        for row_idx in deleted_rows:
            row_idx_int = int(row_idx)
            row_id = original_df.loc[row_idx_int, "id"]
            self.table.delete().eq("id", row_id).execute()

    def sync(self) -> None:
        """Sync the edited dataframe with the Supabase table."""
        # Get the editor state and original dataframe
        editor_state = st.session_state[self.editor_key]
        original_df: pd.DataFrame = st.session_state[f"{self.editor_key}_original"]

        # Get a working copy of the original dataframe to apply edits
        working_df = original_df.copy()

        # Handle edited rows
        if editor_state.get("edited_rows"):
            edited_rows = editor_state["edited_rows"]
            self._edit_rows(edited_rows, working_df)

        # Handle added rows
        if editor_state.get("added_rows"):
            added_rows = editor_state["added_rows"]
            self._add_rows(added_rows)

        # Handle deleted rows
        if editor_state.get("deleted_rows"):
            deleted_rows = editor_state["deleted_rows"]
            self._delete_rows(deleted_rows, original_df)

    def render(self) -> pd.DataFrame:
        """Render the dataframe editor with the original dataframe."""
        # Ensure the original dataframe is in session state
        if f"{self.editor_key}_original" not in st.session_state:
            st.session_state[f"{self.editor_key}_original"] = self.original_df

        # Display data editor with dynamic rows
        return st.data_editor(
            self.original_df,
            key=self.editor_key,
            column_config=self.column_config,
            column_order=self.column_order,
            num_rows="dynamic",
            on_change=self.sync,
        )
