"""Main entry point."""

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
