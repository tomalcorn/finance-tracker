import datetime

import pandas as pd
import streamlit as st

import dataframe_handling as dfh

st.title("Finance Tracker")

prices = [2, 3, 4, 20]
saved = [1, 2, 4, 10]

# Compute progress dynamically
progress = [min(s / p, 1.0) for s, p in zip(saved, prices)]  # cap at 1.0 (100%)

# Create a list of 10 datetime objects starting from now, 1 day apart
date_list = [datetime.date(2025, 5, 31),
             datetime.date(2025, 6, 27),
             datetime.date(2025, 6, 27),
             datetime.date(2025, 6, 27)]

# Print the list
for date in date_list:
    print(date)

# Initialize in session state
if "demo_df" not in st.session_state:
    st.session_state.demo_df = pd.DataFrame({
        "Saved": saved,
        "Price": prices,
        "Progress": progress,
        "Date": date_list,
    })

use_filters = st.checkbox("Add filters")

if use_filters:
    filtered_df = dfh.filter_dataframe(st.session_state.demo_df)
    st.session_state.filtered_df = filtered_df.copy()
    working_df = st.session_state.filtered_df
else:
    working_df = st.session_state.demo_df

# Editable DataFrame with filtered data
edited_df = st.data_editor(
    working_df,
    key="demo_editor",
    num_rows="dynamic",
    column_config={
        "Price": st.column_config.NumberColumn(
            "Price (in GBP)",
            help="The price of the product in GBP",
            min_value=0,
            max_value=1000,
            step=1,
            format="£%d",
        ),
        "Progress": st.column_config.ProgressColumn(
            "Complete",
            help="Amount saved as a percent of price",
            min_value=0,
            max_value=1,
            format="percent",
        ),
        "Date": st.column_config.DateColumn(
            "Date",
            disabled=False,
            format="DD.MM.YYYY"
        )
    },
    hide_index=True,
)

if use_filters:
    # Update filtered_df and merge changes back into demo_df
    st.session_state.filtered_df.update(edited_df)
    st.session_state.demo_df.update(st.session_state.filtered_df)
else:
    st.session_state.demo_df = edited_df