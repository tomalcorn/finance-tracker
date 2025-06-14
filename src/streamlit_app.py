import streamlit as st
import pandas as pd
import time

if "dfa" not in st.session_state:
    st.session_state["dfa"] = pd.DataFrame(
        {
            "Par": ["Apple", "Strawberry", "Banana"],
            "Cat1": ["good", "good", "bad"],
            "Cat2": ["healthy", "healthy", "unhealthy"],
            "Active": [False, False, False],
        }
    )


def active_dfa():
    # Return filtered dataframe with reset index to avoid UI confusion
    # Handle NaN values by filling them with False
    active_col = st.session_state["dfa"]["Active"].fillna(False)
    filtered_df = st.session_state["dfa"][active_col].copy()
    # Store original index in a hidden column for reference
    filtered_df["_original_index"] = filtered_df.index
    # Reset the index for the UI display
    return filtered_df.reset_index(drop=True)


def get_original_index(row):
    # Get the original index from the hidden column
    return active_dfa().iloc[row]["_original_index"]


def commit():
    # Handle edited rows
    if "edited_rows" in st.session_state.editor:
        for row in st.session_state.editor["edited_rows"]:
            original_idx = get_original_index(int(row))
            for key, value in st.session_state.editor["edited_rows"][row].items():
                if key != "_original_index":  # Don't modify our reference column
                    st.session_state["dfa"].at[original_idx, key] = value
    
    # Handle added rows
    if "added_rows" in st.session_state.editor:
        for row in st.session_state.editor["added_rows"]:
            # Create a new row with default values for all columns to prevent NaNs
            new_row = {
                "Par": "",
                "Cat1": "",
                "Cat2": "",
                "Active": True  # Explicitly set to boolean True
            }
            # Update with any user-provided values
            for key, value in row.items():
                if key != "_original_index":  # Don't include our reference column
                    new_row[key] = value
            # Append the new row to the main dataframe
            st.session_state["dfa"] = pd.concat(
                [st.session_state["dfa"], pd.DataFrame([new_row])], 
                ignore_index=True
            )
    
    # Handle deleted rows
    if "deleted_rows" in st.session_state.editor:
        indices_to_delete = []
        for row in st.session_state.editor["deleted_rows"]:
            original_idx = get_original_index(int(row))
            indices_to_delete.append(original_idx)
        
        # Delete rows from the original dataframe
        if indices_to_delete:
            st.session_state["dfa"] = st.session_state["dfa"].drop(indices_to_delete).reset_index(drop=True)


st.header("Filter and edit data")
name = st.text_input("Search for ...")
# Reset all active states first
st.session_state["dfa"]["Active"] = False

if name == "":
    # If no search term, show all rows
    st.session_state["dfa"]["Active"] = True
else:
    # Filter based on search term
    # Handle potential NaN values in Par column
    mask = st.session_state["dfa"]["Par"].fillna("").str.contains(name, case=False)
    st.session_state["dfa"].loc[mask, "Active"] = True

# Display data editor with dynamic rows
edited_dfa = st.data_editor(
    active_dfa(), 
    column_order=["Par", "Cat1", "Cat2"],
    num_rows="dynamic",
    key="editor", 
    on_change=commit
)
# Print for debugging if needed
print(edited_dfa)