"""Payments block for the finance tracker app."""

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities, query
from ui import lookups
from ui.components.buttons import constants
from ui.components.dfes import grid
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


def _current_month_filter() -> query.Filters:
    """Return a payment_date filter covering the current calendar month."""
    start = datetime.datetime.now(tz=datetime.UTC).date().replace(day=1)
    next_month = (start + datetime.timedelta(days=31)).replace(day=1)
    return query.Filters(gte=start, lte=next_month - datetime.timedelta(days=1))


def _build_expense_config(
    bank_account_ids: list[str],
    get_bank_account_name: "Callable",
    expense_source_ids: list[str],
    get_expense_source_name: "Callable",
) -> frontend_models.DFEConfig:
    """Build the grid config for expense payments."""
    return frontend_models.DFEConfig(
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
                filters=_current_month_filter(),
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
    )


def _build_income_config(
    bank_account_ids: list[str],
    get_bank_account_name: "Callable",
    income_source_ids: list[str],
    get_income_source_name: "Callable",
) -> frontend_models.DFEConfig:
    """Build the grid config for income payments."""
    return frontend_models.DFEConfig(
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
                filters=_current_month_filter(),
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
    )


def _configs() -> tuple[
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
    "Callable",
    "Callable",
]:
    """Build both payment grid configs with their shared foreign-key lookups.

    Returns the expense config, income config, and the expense-source and
    bank-account name formatters the breakdown tab also needs.
    """
    bank_account_map = wiring.bank_account_id_name_map()
    bank_account_ids = list(bank_account_map.keys())
    get_bank_account_name = lookups.make_name_formatter(bank_account_map)

    expense_source_map = wiring.expense_source_id_name_map()
    expense_source_ids = list(expense_source_map.keys())
    get_expense_source_name = lookups.make_name_formatter(expense_source_map)

    income_source_map = wiring.income_source_id_name_map()
    income_source_ids = list(income_source_map.keys())
    get_income_source_name = lookups.make_name_formatter(income_source_map)

    expense_config = _build_expense_config(
        bank_account_ids,
        get_bank_account_name,
        expense_source_ids,
        get_expense_source_name,
    )
    income_config = _build_income_config(
        bank_account_ids,
        get_bank_account_name,
        income_source_ids,
        get_income_source_name,
    )
    return expense_config, income_config, get_expense_source_name, get_bank_account_name


def commit() -> None:
    """Apply any pending backend updates for this block."""
    expense_config, income_config, _, _ = _configs()
    grid.commit(expense_config)
    grid.commit(income_config)


def _render_expense_breakdown(
    working_df: pd.DataFrame,
    get_expense_source_name: "Callable",
    get_bank_account_name: "Callable",
) -> None:
    """Render the expense breakdown tab with collapsible sections per source."""
    if working_df.empty:
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
    expense_config, income_config, get_expense_source_name, get_bank_account_name = (
        _configs()
    )

    expense_tab, income_tab, breakdown_tab = st.tabs(
        [
            f"{constants.TabIcons.EXPENSE} Expense Entries",
            f"{constants.TabIcons.INCOME} Income Entries",
            f"{constants.TabIcons.BREAKDOWN} Expense Breakdown",
        ],
    )

    with expense_tab:
        # Build the expense frame explicitly so the breakdown tab can reuse it.
        expense_working_df = grid.build_working_df(expense_config)
        grid.render_buttons(expense_config)
        grid.render_editor(expense_config, expense_working_df)

    with income_tab:
        grid.render(income_config)

    with breakdown_tab:
        _render_expense_breakdown(
            expense_working_df,
            get_expense_source_name,
            get_bank_account_name,
        )
