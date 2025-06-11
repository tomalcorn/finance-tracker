import streamlit as st
import pandas as pd

st.title("Finance Tracker")

random_nums = [1, 2, 4, 10]
demo_df = pd.DataFrame(random_nums, columns=["Nums"])

# Editable DataFrame
st.data_editor(
    demo_df,
    column_config={
        "Nums": st.column_config.NumberColumn(
            "Price (in GBP)",
            help="The price of the product in GBP",
            min_value=0,
            max_value=1000,
            step=1,
            format="£%d",
        )
    },
    hide_index=True,
)