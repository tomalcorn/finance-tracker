"""Main entry point."""

import streamlit as st

import dataframe_handling as dfh

syncer = dfh.DFE(table_name="payments", editor_key="payments_editor")

# Define column configuration
column_config = {
    "description": st.column_config.TextColumn(
        "🔠 Name",
    ),
    "amount": st.column_config.NumberColumn("💵 Price", format="£%.2f"),
    "payment_date": st.column_config.DateColumn("📆 Date", format="localized"),
    "category": st.column_config.SelectboxColumn("⬇️ Category", options=["healthy", "unhealthy"]),
}

edited_df = st.data_editor(
    syncer.original_df,
    key="payments_editor",
    column_config=column_config,
    column_order=["description", "amount", "payment_date", "category"],
    num_rows="dynamic",
    on_change=syncer.sync,
)
