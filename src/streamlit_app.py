"""Main entry point."""

import time

import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection

import dataframe_handling as dfh

# Set up supabase connection
conn = st.connection("supabase", type=SupabaseConnection)

bank_account_names = [
    row["name"] for row in conn.table("bank_accounts").select("name").execute().data
]

# Define column configuration
column_config = {
    "description": st.column_config.TextColumn(
        "🔠 Name",
        required=True,
    ),
    "amount": st.column_config.NumberColumn("💵 Price", format="£%.2f"),
    "payment_date": st.column_config.DateColumn("📆 Date", format="localized"),
    "category": st.column_config.SelectboxColumn(
        "⬇️ Category",
        options=["healthy", "unhealthy"],
    ),
    "bank_account": st.column_config.SelectboxColumn(
        "Bank Account",
        help="Select a bank account",
        options=bank_account_names,
    ),
}
dfe_config = dfh.DFEConfig(
    column_config=column_config,
    column_order=[
        "description",
        "amount",
        "payment_date",
        "category",
        "bank_account",
    ],
    sorts=[("payment_date", "asc")],
)

payments_dfe = dfh.DFE(
    table_name="payments",
    editor_key="payments_editor",
    connection=conn,
    config=dfe_config,
).render()


simple_data = pd.DataFrame(
    {
        "description": ["Groceries", "Gym", "Coffee"],
        "amount": [45.50, 29.99, 3.75],
        "payment_date": pd.to_datetime(["2025-06-01", "2025-06-02", "2025-06-03"]),
        "category": ["healthy", "healthy", "unhealthy"],
        "bank_account": ["Bank A", "Bank B", "Bank A"],
    },
)
modified_data = st.data_editor(
    data=simple_data,
    column_config=column_config,
    num_rows="dynamic",
)

if st.session_state.get("current_df") is not None:
    print(f"simple data pre --------------\n{st.session_state['current_df']}\n")
print(f"simple data post --------------\n{modified_data}\n")
time.sleep(5)
st.session_state["current_df"] = modified_data


"""DFEHandler attempt."""

payments_client = dfh.DFEHandler(
    table_name="payments",
    editor_key="payments_v2",
    connection=conn,
    config=dfe_config,
)

current_df = payments_client.get_original_data()

working_df = st.data_editor(
    data=current_df,
    column_config=payments_client.column_config,
    num_rows="dynamic",
)
