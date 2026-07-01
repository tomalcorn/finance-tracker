"""Payments block for the finance tracker app."""

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities, query
from ui import data_client, lookups
from ui.components.buttons import constants
from ui.components.dfes import base_dfe
from ui.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

_TABLE_NAME = "payments"
_INCOME_KEY_PREFIX = "income_entries"

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
    get_bank_account_name: "Callable",
    expense_source_ids: list[str],
    get_expense_source_name: "Callable",
) -> base_dfe.DFE:
    """Build the DFE for expense payments."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
            ),
            data_source=wiring.payment_data_source(),
            read_via_repository=True,
            backend_model=entities.ExpensePaymentModel,
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
                    sorting=query.SortingValues.DESC,
                    filters=query.Filters(
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
                    filters=query.Filters(eq="expense"),
                ),
            ],
            sample_data=_EXPENSE_PAYMENTS_SAMPLE_DATA,
        ),
    )


def _build_income_dfe(
    bank_account_ids: list[str],
    get_bank_account_name: "Callable",
    income_source_ids: list[str],
    get_income_source_name: "Callable",
) -> base_dfe.DFE:
    """Build the DFE for income payments."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
                key_prefix=_INCOME_KEY_PREFIX,
            ),
            data_source=wiring.payment_data_source(),
            read_via_repository=True,
            backend_model=entities.IncomePaymentModel,
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
                    sorting=query.SortingValues.DESC,
                    filters=query.Filters(
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
                    filters=query.Filters(eq="income"),
                ),
            ],
            sample_data=_INCOME_ENTRIES_SAMPLE_DATA,
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        key_prefix=_TABLE_NAME,
    )
    data_client.commit(
        table_name=_TABLE_NAME,
        key_prefix=_INCOME_KEY_PREFIX,
    )


def _render_expense_breakdown(
    expense_dfe: base_dfe.DFE,
    get_expense_source_name: "Callable",
    get_bank_account_name: "Callable",
) -> None:
    """Render the expense breakdown tab with collapsible sections per source."""
    working_df = expense_dfe.working_df
    if working_df is None or working_df.empty:
        st.info("No expense data available.")
        return

    payments_df = working_df[working_df["payment_type"] == "expense"].copy()
    if payments_df.empty:
        st.info("No expense payments in the current date range.")
        return

    grouped = payments_df.groupby("expense_source_id")
    totals = grouped["expense"].sum().sort_values(ascending=False)

    for source_id in totals.index:
        source_name = get_expense_source_name(source_id)
        total = totals[source_id]
        group_df = grouped.get_group(source_id)

        with st.expander(f"{source_name} — £{total:,.2f}"):
            display_df = group_df[["name", "expense", "bank_account_id"]].copy()
            display_df["bank_account_id"] = display_df["bank_account_id"].map(
                get_bank_account_name,
            )
            display_df.columns = ["Name", "Amount", "Bank Account"]
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Amount": st.column_config.NumberColumn(format="£%.2f"),
                },
            )


def render() -> None:
    """Render the payments block."""
    bank_account_map = lookups.get_id_name_map("bank_accounts")
    bank_account_ids = list(bank_account_map.keys())
    bank_account_name_formatter = lookups.make_name_formatter(bank_account_map)

    expense_source_map = lookups.get_id_name_map("expense_sources")
    expense_source_ids = list(expense_source_map.keys())
    expense_source_name_formatter = lookups.make_name_formatter(expense_source_map)

    income_source_map = lookups.get_id_name_map("income_sources")
    income_source_ids = list(income_source_map.keys())
    income_source_name_formatter = lookups.make_name_formatter(income_source_map)

    expense_tab, income_tab, breakdown_tab = st.tabs(
        [
            f"{constants.TabIcons.EXPENSE} Expense Entries",
            f"{constants.TabIcons.INCOME} Income Entries",
            f"{constants.TabIcons.BREAKDOWN} Expense Breakdown",
        ],
    )

    with expense_tab:
        expense_dfe = _build_expense_dfe(
            bank_account_ids=bank_account_ids,
            get_bank_account_name=bank_account_name_formatter,
            expense_source_ids=expense_source_ids,
            get_expense_source_name=expense_source_name_formatter,
        )
        expense_dfe.load_input_data()
        data_added, filters_changed = expense_dfe.render_buttons()
        expense_dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        expense_dfe.render_editor()

    with income_tab:
        income_dfe = _build_income_dfe(
            bank_account_ids=bank_account_ids,
            get_bank_account_name=bank_account_name_formatter,
            income_source_ids=income_source_ids,
            get_income_source_name=income_source_name_formatter,
        )
        income_dfe.load_input_data()
        data_added, filters_changed = income_dfe.render_buttons()
        income_dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        income_dfe.render_editor()

    with breakdown_tab:
        _render_expense_breakdown(
            expense_dfe=expense_dfe,
            get_expense_source_name=expense_source_name_formatter,
            get_bank_account_name=bank_account_name_formatter,
        )
