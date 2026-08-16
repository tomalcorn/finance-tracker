"""Payments block for the finance tracker app."""

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import query
from driving_adapters import lookups
from driving_adapters.components.buttons import constants
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

    from driving_adapters.components.dfes import data_source as data_source_mod

_GRID_ID = "payments"
_INCOME_GRID_ID = "income_entries"

_EXPENSE_PAYMENTS_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Data"],
        "expense": [0],
        "payment_date": [datetime.datetime.now(tz=datetime.UTC).date().isoformat()],
        "checked": [False],
        "bank_account_id": ["example bank account"],
        "category_id": ["example category"],
        "payment_type": ["expense"],
    },
)

_INCOME_ENTRIES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Income"],
        "income": [0],
        "payment_date": [datetime.datetime.now(tz=datetime.UTC).date().isoformat()],
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


def _current_year_filter() -> query.Filters:
    """Return a payment_date filter covering the current calendar year.

    Income entries are typically logged only once or twice a month, so a
    current-month default (as used for expenses) leaves the tab looking almost
    empty. Defaulting to the current year gives a more useful starting view.
    """
    today = datetime.datetime.now(tz=datetime.UTC).date()
    start = today.replace(month=1, day=1)
    end = today.replace(month=12, day=31)
    return query.Filters(gte=start, lte=end)


def _build_expense_config(
    data_source: "data_source_mod.GridDataSource",
    bank_account_ids: list[str],
    get_bank_account_name: "Callable[[str | float], str]",
    category_ids: list[str],
    get_category_name: "Callable[[str | float], str]",
) -> frontend_models.DFEConfig:
    """Build the grid config for expense payments."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_GRID_ID,
            data_source=data_source,
            # Payments are a discriminated union, so an added row must state its
            # branch for the repository's gate to parse it as an expense.
            extra_row_values={"payment_type": "expense"},
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="What the payment was for.",
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
                        help="When the money moved.",
                        format="localized",
                        required=True,
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
                        help="How much went out.",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Expense",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="checked",
                    column_config=st.column_config.CheckboxColumn(
                        "Checked",
                        help=(
                            "Tick when you have cross checked the account balance "
                            "against your actual account balance."
                        ),
                        required=True,
                    ),
                    button_label="Checked",
                    input_widget=st.checkbox,
                    input_kwargs={"value": False},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="bank_account_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Bank Account",
                        help="Which account the money moved through.",
                        options=bank_account_ids,
                        format_func=get_bank_account_name,
                        required=True,
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
                    column_name="category_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Category",
                        help=(
                            "The budget tracker or expense category this comes out of."
                        ),
                        options=category_ids,
                        format_func=get_category_name,
                    ),
                    button_label="Category",
                    input_widget=st.selectbox,
                    input_kwargs={
                        "options": category_ids,
                        "index": None,
                        "format_func": get_category_name,
                    },
                    format_func=get_category_name,
                    required=False,
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


def _build_income_config(
    data_source: "data_source_mod.GridDataSource",
    bank_account_ids: list[str],
    get_bank_account_name: "Callable[[str | float], str]",
    income_source_ids: list[str],
    get_income_source_name: "Callable[[str | float], str]",
) -> frontend_models.DFEConfig:
    """Build the grid config for income payments."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_INCOME_GRID_ID,
            data_source=data_source,
            # See the expense grid: the union needs its branch stated.
            extra_row_values={"payment_type": "income"},
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="What the payment was for.",
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
                        help="When the money moved.",
                        format="localized",
                        required=True,
                    ),
                    button_label="Payment Date",
                    input_widget=st.date_input,
                    sorting=query.SortingValues.DESC,
                    filters=_current_year_filter(),
                ),
                frontend_models.DFEColumnConfig(
                    column_name="income",
                    column_config=st.column_config.NumberColumn(
                        "Income",
                        help="How much came in.",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Income",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="checked",
                    column_config=st.column_config.CheckboxColumn(
                        "Checked",
                        help=(
                            "Tick when you have cross checked the account balance "
                            "against your actual account balance."
                        ),
                        required=True,
                    ),
                    button_label="Checked",
                    input_widget=st.checkbox,
                    input_kwargs={"value": False},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="bank_account_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Bank Account",
                        help="Which account the money moved through.",
                        options=bank_account_ids,
                        format_func=get_bank_account_name,
                        required=True,
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
                        help="Which income source this income goes against.",
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
                    required=False,
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


def _configs(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    category_map: dict[str, str],
    income_source_map: dict[str, str],
) -> tuple[
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
    "Callable[[str | float], str]",
    "Callable[[str | float], str]",
]:
    """Build both payment grid configs with their shared foreign-key lookups.

    Returns the expense config, income config, and the expense-source and
    bank-account name formatters the breakdown tab also needs.
    """
    bank_account_ids = list(bank_account_map.keys())
    get_bank_account_name = lookups.make_name_formatter(bank_account_map)

    category_ids = list(category_map.keys())
    get_category_name = lookups.make_name_formatter(category_map)

    income_source_ids = list(income_source_map.keys())
    get_income_source_name = lookups.make_name_formatter(income_source_map)

    expense_config = _build_expense_config(
        data_source,
        bank_account_ids,
        get_bank_account_name,
        category_ids,
        get_category_name,
    )
    income_config = _build_income_config(
        data_source,
        bank_account_ids,
        get_bank_account_name,
        income_source_ids,
        get_income_source_name,
    )
    return expense_config, income_config, get_category_name, get_bank_account_name


def commit(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    category_map: dict[str, str],
    income_source_map: dict[str, str],
) -> None:
    """Apply any pending backend updates for this block."""
    expense_config, income_config, _, _ = _configs(
        data_source,
        bank_account_map,
        category_map,
        income_source_map,
    )
    grid.commit(expense_config)
    grid.commit(income_config)


def _render_expense_breakdown(
    working_df: pd.DataFrame,
    get_category_name: "Callable[[str | float], str]",
    get_bank_account_name: "Callable[[str | float], str]",
) -> None:
    """Render the expense breakdown tab with collapsible sections per source."""
    if working_df.empty:
        st.info("No expense data available.")
        return

    payments_df = working_df[working_df["payment_type"] == "expense"].copy()
    if payments_df.empty:
        st.info("No expense payments in the current date range.")
        return

    grouped = payments_df.groupby("category_id")
    totals = grouped["expense"].sum().sort_values(ascending=False)

    for source_id in totals.index:
        source_name = get_category_name(source_id)
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
                width="stretch",
                hide_index=True,
                column_config={
                    "Amount": st.column_config.NumberColumn(format="£%.2f"),
                },
            )


def render(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    category_map: dict[str, str],
    income_source_map: dict[str, str],
) -> None:
    """Render the payments block."""
    expense_config, income_config, get_category_name, get_bank_account_name = _configs(
        data_source,
        bank_account_map,
        category_map,
        income_source_map,
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
        grid.render_editor(
            expense_config.display,
            expense_config.grid_id,
            expense_working_df,
        )

    with income_tab:
        grid.render(income_config)

    with breakdown_tab:
        _render_expense_breakdown(
            expense_working_df,
            get_category_name,
            get_bank_account_name,
        )
