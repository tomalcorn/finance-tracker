"""Main entry point."""

import uuid

import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection

import dataframe_handling as dfh

# Set up supabase connection
conn = st.connection("supabase", type=SupabaseConnection)

bank_account_names = [
    row["name"] for row in conn.table("bank_accounts").select("name").execute().data
]

# Define column and add button configuration
payments_config = [
    dfh.DFEColumnConfig(
        column="description",
        column_config=st.column_config.TextColumn(
            "🔠 Name",
            required=True,
        ),
        button_label="Name",
        input_widget=st.text_input,
        input_kwargs={
            "value": None,
        },
    ),
    dfh.DFEColumnConfig(
        column="amount",
        column_config=st.column_config.NumberColumn(
            "💵 Amount",
            format="£%.2f",
        ),
        button_label="Amount",
        input_widget=st.number_input,
        input_kwargs={
            "value": None,
            "format": "%.2f",
        },
    ),
    dfh.DFEColumnConfig(
        column="payment_date",
        column_config=st.column_config.DateColumn(
            "📆 Date",
            format="localized",
        ),
        button_label="Payment Date",
        input_widget=st.date_input,
        sorting="asc",
    ),
    dfh.DFEColumnConfig(
        column="category",
        column_config=st.column_config.SelectboxColumn(
            "⬇️ Category",
            options=["healthy", "unhealthy"],
        ),
        button_label="Category",
        input_widget=st.selectbox,
        input_kwargs={
            "options": ["healthy", "unhealthy"],
            "index": None,
        },
    ),
    dfh.DFEColumnConfig(
        column="bank_account",
        column_config=st.column_config.SelectboxColumn(
            "Bank Account",
            help="Select a bank account",
            options=bank_account_names,
        ),
        button_label="Bank Account",
        input_widget=st.selectbox,
        input_kwargs={
            "options": bank_account_names,
            "index": None,
        },
    ),
]
payments_order = [
    "description",
    "amount",
    "payment_date",
    "category",
    "bank_account",
]
sample_data = pd.DataFrame(
    {
        "id": [str(uuid.uuid4())],
        "description": ["Example Data"],
        "amount": [0],
        "payment_date": ["2025-06-01"],
        "category": ["category"],
        "created_at": ["2025-06-01"],
        "bank_account": [bank_account_names[0]],
    },
)
payments_dfe = dfh.DFE(
    table_name="payments",
    sample_data=sample_data,
    connection=conn,
    config=payments_config,
    column_order=payments_order,
)

modified_payments = payments_dfe.render()

payments_dfe.write_changes_to_backend(modified_payments)
