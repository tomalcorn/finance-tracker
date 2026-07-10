"""Subscriptions block for managing recurring payments."""

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities
from driving_adapters import lookups
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

    from driving_adapters.components.dfes import data_source as data_source_mod

_TABLE_NAME = "subscriptions"

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
    data_source: "data_source_mod.GridDataSource",
    bank_account_ids: list[str],
    get_bank_account_name: "Callable[[str | float], str]",
    expense_source_ids: list[str],
    get_expense_source_name: "Callable[[str | float], str]",
) -> frontend_models.DFEConfig:
    """Build the grid config for the subscriptions block."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_TABLE_NAME,
        ),
        data_source=data_source,
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


def _config(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
) -> frontend_models.DFEConfig:
    """Build the subscriptions grid config with its foreign-key lookups."""
    return _build_config(
        data_source,
        list(bank_account_map.keys()),
        lookups.make_name_formatter(bank_account_map, "Unknown Bank Account"),
        list(expense_source_map.keys()),
        lookups.make_name_formatter(expense_source_map, "Unknown Expense Source"),
    )


def commit(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
) -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_config(data_source, bank_account_map, expense_source_map))


def render(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
) -> None:
    """Render the subscriptions block."""
    grid.render(_config(data_source, bank_account_map, expense_source_map))
