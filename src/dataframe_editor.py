import datetime
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)


class DFEWithFilters:
    """
    A class that provides Streamlit dataframe editing functionality with filtering,
    search, and CRUD operations that maintain the original dataframe structure.
    """
    
    def __init__(
        self, 
        df: pd.DataFrame,
        session_key: str = "dfa",
        column_config: Optional[Dict] = None,
        column_order: Optional[List[str]] = None
    ):
        """
        Initialize the DataframeEditor with a pandas DataFrame.
        
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
        """Get the current dataframe from session state"""
        return st.session_state[self.session_key]
        
    def active_df(self) -> pd.DataFrame:
        """
        Return filtered dataframe with reset index to avoid UI confusion
        """
        # Handle NaN values by filling them with False
        active_col = self.df["Active"].fillna(False)
        filtered_df = self.df[active_col].copy()
        # Store original index in a hidden column for reference
        filtered_df["_original_index"] = filtered_df.index
        # Reset the index for the UI display
        return filtered_df.reset_index(drop=True)
    
    def get_original_index(self, row: int) -> int:
        """
        Get the original index from the hidden column
        """
        return self.active_df().iloc[row]["_original_index"]
    
    def commit(self):
        """
        Commit changes from the data editor to the session state dataframe
        """
        # Handle edited rows
        if "edited_rows" in st.session_state[self.editor_key]:
            for row in st.session_state[self.editor_key]["edited_rows"]:
                original_idx = self.get_original_index(int(row))
                for key, value in st.session_state[self.editor_key]["edited_rows"][row].items():
                    if key != "_original_index":  # Don't modify our reference column
                        self.df.at[original_idx, key] = value
        
        # Handle added rows
        if "added_rows" in st.session_state[self.editor_key]:
            for row in st.session_state[self.editor_key]["added_rows"]:
                # Get all columns from the dataframe
                new_row = {}
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

                # Set Active to True
                new_row["Active"] = True
                
                # Update with any user-provided values
                for key, value in row.items():
                    if key != "_original_index":  # Don't include our reference column
                        new_row[key] = value
                
                # Append the new row to the main dataframe
                st.session_state[self.session_key] = pd.concat(
                    [self.df, pd.DataFrame([new_row])], 
                    ignore_index=True
                )
                st.session_state[f"{self.session_key}_newly_added_row"] = new_row
        
        # Handle deleted rows
        if "deleted_rows" in st.session_state[self.editor_key]:
            indices_to_delete = []
            for row in st.session_state[self.editor_key]["deleted_rows"]:
                original_idx = self.get_original_index(int(row))
                indices_to_delete.append(original_idx)
            
            # Delete rows from the original dataframe
            if indices_to_delete:
                st.session_state[self.session_key] = self.df.drop(indices_to_delete).reset_index(drop=True)
    
    def filter_dataframe(self):
        """
        Filter the dataframe based on filters from the multiselect
        """
        # Reset all active states first
        self.df["Active"] = False
        
        # Get filter mask from UI components
        mask = self.get_filter_mask()
        
        # Also mark true if row matches newly added row
        if st.session_state[f"{self.session_key}_newly_added_row"] is not None:
            new_row = st.session_state[f"{self.session_key}_newly_added_row"]
            # Compare only the relevant columns for matching
            match_new_row = pd.Series(True, index=self.df.index)
            for col in self.df.columns:
                if col in new_row and col != "Active":
                    col_match = (self.df[col] == new_row[col])
                    match_new_row &= col_match
            
            mask = mask | match_new_row
            
        self.df.loc[mask, "Active"] = True
    
    def get_filter_mask(self):
        """
        Display filter options for the dataframe. Return a mask for filtering.
        """
        # Initialize mask with all True values
        mask = pd.Series(True, index=self.df.index)

        for col in self.df.columns:
            if is_object_dtype(self.df[col]):
                try:
                    self.df[col] = pd.to_datetime(self.df[col])
                except Exception:
                    pass

            if is_datetime64_any_dtype(self.df[col]):
                self.df[col] = self.df[col].dt.tz_localize(None)
        
        modification_container = st.expander(label="Filter Options")
        
        with modification_container:
            to_filter_columns = st.multiselect("Filter dataframe on", self.df.columns)
            
            for column in to_filter_columns:
                left, right = st.columns((1, 20))
                # Treat columns with < 10 unique values as categorical
                # - no but if you want to then ( or df[column].nunique() < 10)
                if is_object_dtype(self.df[column]) and len(self.df[column].unique()) < 20:
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
                    if len(user_date_input) == 2:
                        user_date_input = tuple(map(pd.to_datetime, user_date_input)) # type: ignore
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
        """
        Render the dataframe editor with filter functionality
        
        Returns:
            The edited dataframe
        """
        # Filter dataframe based on UI filters
        self.filter_dataframe()
        
        # Prepare column config if not provided
        if self.column_config is None:
            self.column_config = {}
        
        # Display data editor with dynamic rows
        edited_df = st.data_editor(
            self.active_df(),
            column_order=self.column_order,
            column_config=self.column_config,
            num_rows="dynamic",
            key=self.editor_key,
            on_change=self.commit
        )
        
        return edited_df
    

# Example usage:
if __name__ == "__main__":
    # Example DataFrame
    initial_data = pd.DataFrame(
        {
            "Par": ["Apple", "Strawberry", "Banana"],
            "Cat1": ["good", "good", "bad"],
            "Cat2": ["healthy", "healthy", "unhealthy"],
            "Price": [1.2, 2.5, 0.8],
            "Dates": [datetime.date(2025, 1, 1),
                      datetime.date(2025, 2, 1), 
                     datetime.date(2025, 3, 1)], 
            "Active": [False, False, False],
        }
    )
    
    # Define column configuration
    column_config = {
        "Par": st.column_config.TextColumn(
            "🍎 Product",
            ),
        "Cat1": st.column_config.SelectboxColumn("Category 1", options=["good", "bad"]),
        "Cat2": st.column_config.SelectboxColumn("Category 2", options=["healthy", "unhealthy"]),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Dates": st.column_config.DateColumn("Date", format="localized"),
    }
    
    # Create DataframeEditor instance
    df_editor = DFEWithFilters(
        df=initial_data,
        session_key="dfa",
        column_config=column_config,
        column_order=["Par", "Cat1", "Cat2", "Price", "Dates"]
    )
    
    # Render the UI
    st.header("Filter and edit data")
    
    # Render the data editor with filters from the UI
    edited_df = df_editor.render()
    
    # Print for debugging if needed
    print(edited_df)
