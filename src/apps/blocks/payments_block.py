"""Payments block for the finance tracker app."""

import datetime

import pandas as pd
import streamlit as st

from apps.blocks import base_block
from libs import data_client
from libs.buttons import constants
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_TABLE_NAME = dfe_constants.TableNames.PAYMENTS.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
]

_SAMPLE_DATA = pd.DataFrame(
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


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
    )


def render() -> None:
    """Render the payments block."""
    bank_accounts_data = data_client.get_data(
        table_name="bank_accounts",
        query_string="*",
    )
    bank_account_map: dict[str, str] = {
        str(ba["id"]): str(ba["name"]) for ba in bank_accounts_data
    }
    bank_account_ids = list(bank_account_map.keys())

    def get_bank_account_name(ba_id: str | float) -> str:
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
        return expense_source_map.get(str(es_id), "Unknown Expense Source")

    base_block.render_dfe_tab(
        table_names=frontend_models.DFETableNameConfig(write_table=_TABLE_NAME),
        backend_model=backend_models.PaymentsModel,
        configs=[
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config=st.column_config.TextColumn("🔠 Name", required=True),
                button_label="Name",
                input_widget=st.text_input,
                input_kwargs={"value": None},
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
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            frontend_models.DFEColumnConfig(
                column_name="checked",
                column_config=st.column_config.CheckboxColumn("✅ Checked"),
                button_label="Checked",
                input_widget=st.checkbox,
                input_kwargs={"value": False},
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
        ],
        sample_data=_SAMPLE_DATA,
    )
