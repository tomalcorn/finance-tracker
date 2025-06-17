"""Main entry point."""

import streamlit as st
from st_supabase_connection import SupabaseConnection

import dataframe_handling as dfh

# Set up supabase connection
conn = st.connection("supabase", type=SupabaseConnection)

# Define column configuration
column_config = {
    "description": st.column_config.TextColumn(
        "🔠 Name",
    ),
    "amount": st.column_config.NumberColumn("💵 Price", format="£%.2f"),
    "payment_date": st.column_config.DateColumn("📆 Date", format="localized"),
    "category": st.column_config.SelectboxColumn(
        "⬇️ Category",
        options=["healthy", "unhealthy"],
    ),
}

payments_dfe = dfh.DFE(
    table_name="payments",
    editor_key="payments_editor",
    connection=conn,
    column_config=column_config,
    column_order=[
        "description",
        "amount",
        "payment_date",
        "category",
    ],
).render()
