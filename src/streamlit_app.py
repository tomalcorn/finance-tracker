"""Main entry point."""

import uuid

import pandas as pd
import streamlit as st
import supabase_auth
from st_supabase_connection import SupabaseConnection

from apps import data_client
from apps.buttons import filter_button, sort_button
from libs import constants, frontend_models
from libs.buttons import add_button
from libs.dfes import base_dfe

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
bank_accounts = data_client.get_data(
    table_name="bank_accounts",
    query_string="*",
)
bank_account_map = {ba["id"]: ba["name"] for ba in bank_accounts}
bank_account_ids = list(bank_account_map.keys())

expense_sources = data_client.get_data(
    table_name="expense_sources",
    query_string="*",
)
expense_source_map = {es["id"]: es["name"] for es in expense_sources}
expense_source_ids = list(expense_source_map.keys())

# === Payments DFE ===

payments_add_button = add_button.AddButton(table_name="payments")
payments_sort_button = sort_button.SortButton(table_name="payments")
payments_filter_button = filter_button.FilterButton(table_name="payments")

# Define column and add button configuration
payments_configs = [
    frontend_models.DFEColumnConfig(
        column_name="name",
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
        column_name="payment_date",
        column_config=st.column_config.DateColumn(
            "📆 Date",
            format="localized",
        ),
        button_label="Payment Date",
        input_widget=st.date_input,
        sorting=constants.SortingValues.DESC,
        filters=frontend_models.Filters(gte="2024-01-01", lte="2025-12-31"),
    ),
    frontend_models.DFEColumnConfig(
        column_name="expense",
        column_config=st.column_config.NumberColumn(
            "💵 Expense",
            format="£%.2f",
        ),
        button_label="Expense",
        input_widget=st.number_input,
        input_kwargs={
            "value": None,
            "format": "%.2f",
        },
    ),
    frontend_models.DFEColumnConfig(
        column_name="checked",
        column_config=st.column_config.CheckboxColumn(
            "✅ Checked",
        ),
        button_label="Checked",
        input_widget=st.checkbox,
        input_kwargs={
            "value": False,
        },
    ),
    frontend_models.DFEColumnConfig(
        column_name="bank_account_id",
        column_config=st.column_config.SelectboxColumn(
            "Bank Account",
            help="Select a bank account",
            options=bank_account_ids,
            format_func=lambda x: bank_account_map.get(x, x),
        ),
        button_label="Bank Account",
        input_widget=st.selectbox,
        input_kwargs={
            "options": bank_account_ids,
            "index": None,
            "format_func": lambda x: bank_account_map.get(x, x),
        },
    ),
    frontend_models.DFEColumnConfig(
        column_name="expense_source_id",
        column_config=st.column_config.SelectboxColumn(
            "Expense Source",
            help="Select an expense source",
            options=expense_source_ids,
            format_func=lambda x: expense_source_map.get(x, x),
        ),
        button_label="Expense Source",
        input_widget=st.selectbox,
        input_kwargs={
            "options": expense_source_ids,
            "index": None,
            "format_func": lambda x: expense_source_map.get(x, x),
        },
    ),
]
sample_data = pd.DataFrame(
    {
        "id": [str(uuid.uuid4())],
        "name": ["Example Data"],
        "expense": [0],
        "payment_date": ["2025-06-01"],
        "checked": [False],
        "created_at": ["2025-06-01"],
        "bank_account_id": [bank_account_ids[0]],
        "expense_source_id": [expense_source_ids[0]],
    },
)

# Call buttons
button_cols = st.columns(3)
with button_cols[0]:
    payments_add_button(col_configs=payments_configs)
with button_cols[1]:
    payments_configs = payments_sort_button(col_configs=payments_configs)
with button_cols[2]:
    payments_configs = payments_filter_button(col_configs=payments_configs)

payments_dfe_new = base_dfe.DFE(
    table_name="payments",
    configs=payments_configs,
)

modified_payments_new = payments_dfe_new.load_input_data(sample_data).render()
backend_updates = payments_dfe_new.sync(modified_payments_new)
data_client.update_backend(
    table_name="payments",
    updates=backend_updates,
    connection=conn,
)
