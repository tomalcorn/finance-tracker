"""Subscriptions block for managing recurring payments."""

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities
from ui.components.dfes import grid
from ui.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

_TABLE_NAME = "subscriptions"
_VIEW_NAME = "subscriptions_view"

_CADENCE_OPTIONS = ["weekly", "monthly", "quarterly", "biannually", "yearly"]

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Subscription"],
        "amount": [0.0],
        "cadence": ["monthly"],
        "bank_account_id": ["example bank account"],
        "expense_source_id": ["example expense source"],
        "start_date": [datetime.datetime.now(tz=datetime.UTC).date().isoformat()],
        "end_date": [None],
        "is_active": [True],
        "monthly_cost": [0.0],
    },
)


def _build_config(
    bank_account_ids: list[str],
    get_bank_account_name: "Callable",
    expense_source_ids: list[str],
    get_expense_source_name: "Callable",
) -> frontend_models.DFEConfig:
    """Build the grid config for the subscriptions block."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_TABLE_NAME,
            read_table=_VIEW_NAME,
        ),
        data_source=wiring.subscription_data_source(),
        read_via_repository=True,
        backend_model=entities.SubscriptionModel,
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
                column_name="amount",
                column_config=st.column_config.NumberColumn(
                    "Amount",
                    format="£%.2f",
                ),
                button_label="Amount",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            frontend_models.DFEColumnConfig(
                column_name="cadence",
                column_config=st.column_config.SelectboxColumn(
                    "Cadence",
                    options=_CADENCE_OPTIONS,
                ),
                button_label="Cadence",
                input_widget=st.selectbox,
                input_kwargs={
                    "options": _CADENCE_OPTIONS,
                    "index": 2,
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
            frontend_models.DFEColumnConfig(
                column_name="start_date",
                column_config=st.column_config.DateColumn(
                    "Start Date",
                    format="localized",
                ),
                button_label="Start Date",
                input_widget=st.date_input,
            ),
            frontend_models.DFEColumnConfig(
                column_name="end_date",
                column_config=st.column_config.DateColumn(
                    "End Date",
                    format="localized",
                ),
                button_label="End Date",
                input_widget=st.date_input,
                input_kwargs={"value": None},
                required=False,
            ),
            frontend_models.DFEColumnConfig(
                column_name="is_active",
                column_config=st.column_config.CheckboxColumn("Active"),
                button_label="Active",
                input_widget=st.checkbox,
                input_kwargs={"value": True},
            ),
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="monthly_cost",
                column_config=st.column_config.NumberColumn(
                    "Monthly Cost",
                    format="£%.2f",
                    disabled=True,
                ),
                button_label="Monthly Cost",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
        ],
        sample_data=_SAMPLE_DATA,
    )


def _config() -> frontend_models.DFEConfig:
    """Build the subscriptions grid config with its foreign-key lookups."""
    bank_account_map = wiring.bank_account_id_name_map()
    bank_account_ids = list(bank_account_map.keys())

    def get_bank_account_name(ba_id: str | float) -> str:
        return bank_account_map.get(str(ba_id), "Unknown Bank Account")

    expense_source_map = wiring.expense_source_id_name_map()
    expense_source_ids = list(expense_source_map.keys())

    def get_expense_source_name(es_id: str | float) -> str:
        return expense_source_map.get(str(es_id), "Unknown Expense Source")

    return _build_config(
        bank_account_ids,
        get_bank_account_name,
        expense_source_ids,
        get_expense_source_name,
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_config())


def render() -> None:
    """Render the subscriptions block."""
    grid.render(_config())
