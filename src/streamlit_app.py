"""Main entry point."""

import uuid

import pandas as pd
import streamlit as st
import supabase_auth
from st_supabase_connection import SupabaseConnection

import libs.dataframe_handling as dfh
from libs import constants, frontend_models, utils

# Set up supabase connection and authenticate user
conn = st.connection("supabase", type=SupabaseConnection)

email_password_creds = supabase_auth.SignInWithEmailAndPasswordCredentials(
    email="tomalcorn777@icloud.com",
    password="REDACTED",  # noqa: S106 - only temporary for dev testing
)

with st.spinner("Signing in..."):
    auth_resp = conn.auth.sign_in_with_password(email_password_creds)

    access_token = None
    user = None

    # Support multiple response shapes (object or dict)
    if hasattr(auth_resp, "session") and auth_resp.session:
        access_token = auth_resp.session.access_token
        user = auth_resp.user

    if not access_token:
        st.error("Authentication failed. Please check your credentials.")
        st.stop()

    conn.client.postgrest.auth(access_token)
    st.session_state[constants.SSKeys.CURRENT_USER] = user

# Get bank accounts from the database
bank_accounts = utils.get_original_data(
    table_name="bank_accounts",
    query_string="*",
)
bank_name_id_map = {account["name"]: account["id"] for account in bank_accounts}
bank_account_names = list(bank_name_id_map.keys())

# Define column and add button configuration
payments_config = [
    frontend_models.DFEColumnConfig(
        column_name="description",
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
    frontend_models.DFEColumnConfig(
        column_name="amount",
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
    frontend_models.DFEColumnConfig(
        column_name="payment_date",
        column_config=st.column_config.DateColumn(
            "📆 Date",
            format="localized",
        ),
        button_label="Payment Date",
        input_widget=st.date_input,
        sorting="asc",
        filtering=config.Filters(gte="2024-01-01", lte="2025-12-31"),
    ),
    frontend_models.DFEColumnConfig(
        column_name="category",
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
    frontend_models.DFEColumnConfig(
        column_name="bank_account_id",
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
        foreign_key_mapping=bank_name_id_map,
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
        "bank_account": ["Example bank account"],
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
