import streamlit as st
import pandas as pd

st.title("Finance Tracker")

prices = [2, 3, 4, 20]
saved = [1, 2, 4, 10]

# Compute progress dynamically
progress = [min(s / p, 1.0) for s, p in zip(saved, prices)]  # cap at 1.0 (100%)

# Create DataFrame
demo_df = pd.DataFrame({
    "Saved": saved,
    "Price": prices,
    "Progress": progress,
})

# Editable DataFrame
st.data_editor(
    demo_df,
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
    },
    hide_index=True,
)