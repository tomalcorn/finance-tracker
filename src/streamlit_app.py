"""Main entry point."""

import datetime

import pandas as pd
import streamlit as st

from apps import data_client
from apps.buttons import add_button, filter_button
from libs.dfes import base_dfe
from libs.models import backend_models, constants, frontend_models

filter_col, empty_col, add_col = st.columns([0.3, 0.4, 0.3])

# Get bank accounts from the database
bank_accounts = data_client.get_data(
    table_name="bank_accounts",
    query_string="*",
)
bank_account_map: dict[str, str] = {
    str(ba["id"]): str(ba["name"]) for ba in bank_accounts
}
bank_account_ids = list(bank_account_map.keys())


def get_bank_account_name(ba_id: str | float) -> str:
    """Get the bank account name for a given ID."""
    return bank_account_map.get(str(ba_id), "Unknown Bank Account")


expense_sources = data_client.get_data(
    table_name="expense_sources",
    query_string="*",
)
expense_source_map: dict[str, str] = {
    str(es["id"]): str(es["name"]) for es in expense_sources
}
expense_source_ids = list(expense_source_map.keys())


def get_expense_source_name(es_id: str | float) -> str:
    """Get the expense source name for a given ID."""
    return expense_source_map.get(str(es_id), "Unknown Expense Source")


# === Payments DFE ===

payments_add_button = add_button.AddButton(
    table_name="payments",
    backend_model=backend_models.PaymentsModel,
)
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
        filters=frontend_models.Filters(
            gte=datetime.date(2026, 1, 1),
            lte=datetime.date(2026, 12, 31),
        ),
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
            format_func=get_bank_account_name,
        ),
        button_label="Bank Account",
        input_widget=st.selectbox,
        input_kwargs={
            "options": bank_account_ids,
            "index": None,
            "format_func": get_bank_account_name,
        },
        format_func=get_bank_account_name,
    ),
    frontend_models.DFEColumnConfig(
        column_name="expense_source_id",
        column_config=st.column_config.SelectboxColumn(
            "Expense Source",
            help="Select an expense source",
            options=expense_source_ids,
            format_func=get_expense_source_name,
        ),
        button_label="Expense Source",
        input_widget=st.selectbox,
        input_kwargs={
            "options": expense_source_ids,
            "index": None,
            "format_func": get_expense_source_name,
        },
        format_func=get_expense_source_name,
    ),
]
sample_data = pd.DataFrame(
    {
        "name": ["Example Data"],
        "expense": [0],
        "payment_date": ["2025-06-01"],
        "checked": [False],
        "created_at": ["2025-06-01"],
        "bank_account_id": ["example bank account"],
        "expense_source_id": ["example expense source"],
    },
)

# Call buttons
with add_col:
    new_data_added = payments_add_button(col_configs=payments_configs)
with filter_col:
    filters_changed, payments_configs = payments_filter_button(
        col_configs=payments_configs,
    )

payments_dfe_new = base_dfe.DFE(
    table_name="payments",
    configs=payments_configs,
)

payments_dfe_new.load_input_data(
    sample_data,
    filters_changed=filters_changed,
    new_data_added=new_data_added,
).render()
data_client.update_backend(
    table_name="payments",
    updates=payments_dfe_new.backend_updates,
)
