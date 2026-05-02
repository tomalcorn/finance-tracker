"""Payments block for the finance tracker app."""

import datetime
from collections.abc import Callable

import pandas as pd
import streamlit as st

from libs import data_client
from libs.buttons import constants
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_TABLE_NAME = dfe_constants.TableNames.PAYMENTS.value
_INCOME_KEY_PREFIX = "income_entries"
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    dfe_constants.TableNames.EXPENSE_SOURCES,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
    dfe_constants.TableNames.INCOME_SOURCES,
    dfe_constants.TableNames.INCOME_SOURCES_VIEW,
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.BUDGET_TRACKER_VIEW,
]

_EXPENSE_PAYMENTS_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Data"],
        "expense": [0],
        "payment_date": ["2025-06-01"],
        "checked": [False],
        "bank_account_id": ["example bank account"],
        "expense_source_id": ["example expense source"],
        "payment_type": ["expense"],
    },
)

_INCOME_ENTRIES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Income"],
        "income": [0],
        "payment_date": ["2025-06-01"],
        "checked": [False],
        "bank_account_id": ["example bank account"],
        "income_source_id": ["example income source"],
        "payment_type": ["income"],
    },
)


def _build_expense_dfe(
    bank_account_ids: list[str],
    get_bank_account_name: Callable,
    expense_source_ids: list[str],
    get_expense_source_name: Callable,
) -> base_dfe.DFE:
    """Build the DFE for expense payments."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
            ),
            backend_model=backend_models.ExpensePaymentModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        required=True,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="payment_date",
                    column_config=st.column_config.DateColumn(
                        "Date",
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
                        "Expense",
                        format="£%.2f",
                    ),
                    button_label="Expense",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="checked",
                    column_config=st.column_config.CheckboxColumn(
                        "Checked",
                    ),
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
                frontend_models.DFEColumnConfig(
                    column_name="payment_type",
                    column_config=st.column_config.TextColumn("Type"),
                    input_widget=st.text_input,
                    visible=False,
                    filters=frontend_models.Filters(eq="expense"),
                ),
            ],
            sample_data=_EXPENSE_PAYMENTS_SAMPLE_DATA,
            tables_to_clear=_TABLES_TO_CLEAR,
        ),
    )


def _build_income_dfe(
    bank_account_ids: list[str],
    get_bank_account_name: Callable,
    income_source_ids: list[str],
    get_income_source_name: Callable,
) -> base_dfe.DFE:
    """Build the DFE for income payments."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
                key_prefix=_INCOME_KEY_PREFIX,
            ),
            backend_model=backend_models.IncomePaymentModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        required=True,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="payment_date",
                    column_config=st.column_config.DateColumn(
                        "Date",
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
                    column_name="income",
                    column_config=st.column_config.NumberColumn(
                        "Income",
                        format="£%.2f",
                    ),
                    button_label="Income",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="checked",
                    column_config=st.column_config.CheckboxColumn(
                        "Checked",
                    ),
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
                    column_name="income_source_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Income Source",
                        help="Select an income source",
                        options=income_source_ids,
                        format_func=get_income_source_name,
                    ),
                    button_label="Income Source",
                    input_widget=st.selectbox,
                    input_kwargs={
                        "options": income_source_ids,
                        "index": None,
                        "format_func": get_income_source_name,
                    },
                    format_func=get_income_source_name,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="payment_type",
                    column_config=st.column_config.TextColumn("Type"),
                    input_widget=st.text_input,
                    visible=False,
                    filters=frontend_models.Filters(eq="income"),
                ),
            ],
            sample_data=_INCOME_ENTRIES_SAMPLE_DATA,
            tables_to_clear=_TABLES_TO_CLEAR,
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
        key_prefix=_TABLE_NAME,
    )
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
        key_prefix=_INCOME_KEY_PREFIX,
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

    income_sources = data_client.get_data(
        table_name="income_sources",
        query_string="*",
    )
    income_source_map: dict[str, str] = {
        str(ins["id"]): str(ins["name"]) for ins in income_sources
    }
    income_source_ids = list(income_source_map.keys())

    def get_income_source_name(ins_id: str | float) -> str:
        return income_source_map.get(str(ins_id), "Unknown Income Source")

    expense_tab, income_tab = st.tabs(
        [
            f"{constants.TabIcons.EXPENSE} Expense Entries",
            f"{constants.TabIcons.INCOME} Income Entries",
        ],
    )

    with expense_tab:
        expense_dfe = _build_expense_dfe(
            bank_account_ids,
            get_bank_account_name,
            expense_source_ids,
            get_expense_source_name,
        )
        expense_dfe.load_input_data()
        expense_dfe.render()

    with income_tab:
        income_dfe = _build_income_dfe(
            bank_account_ids,
            get_bank_account_name,
            income_source_ids,
            get_income_source_name,
        )
        income_dfe.load_input_data()
        income_dfe.render()
