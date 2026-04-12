"""Block for the budget tracker section: budget tracker, expense and income sources."""

import pandas as pd
import streamlit as st

from apps.blocks import base_block
from libs import data_client
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_BUDGET_TRACKER_TABLE = dfe_constants.TableNames.BUDGET_TRACKER.value

_EXPENSE_SOURCES_TABLE = dfe_constants.TableNames.EXPENSE_SOURCES.value
_EXPENSE_SOURCES_VIEW = dfe_constants.TableNames.EXPENSE_SOURCES_VIEW.value

_INCOME_SOURCES_TABLE = dfe_constants.TableNames.INCOME_SOURCES.value
_INCOME_SOURCES_VIEW = dfe_constants.TableNames.INCOME_SOURCES_VIEW.value


_BUDGET_TRACKER_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.EXPENSE_SOURCES,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
    dfe_constants.TableNames.INCOME_SOURCES,
    dfe_constants.TableNames.INCOME_SOURCES_VIEW,
]

_BUDGET_TRACKER_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Budget Tracker"],
        "total_budget": [0],
        "current_month": [0],
    },
)

_EXPENSE_SOURCES_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.EXPENSE_SOURCES,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
]


_EXPENSE_SOURCES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Expense Source"],
        "budget": [0],
        "current_month": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)

_INCOME_SOURCES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Income Source"],
        "current_month": [0],
        "budget_tracker_ids": [[]],
    },
)

_INCOME_SOURCES_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.INCOME_SOURCES,
    dfe_constants.TableNames.INCOME_SOURCES_VIEW,
]


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_BUDGET_TRACKER_TABLE,
        tables_to_clear=_BUDGET_TRACKER_TABLES_TO_CLEAR,
    )
    data_client.commit(
        table_name=_EXPENSE_SOURCES_TABLE,
        tables_to_clear=_EXPENSE_SOURCES_TABLES_TO_CLEAR,
    )
    data_client.commit(
        table_name=_INCOME_SOURCES_TABLE,
        tables_to_clear=_INCOME_SOURCES_TABLES_TO_CLEAR,
    )


def render() -> None:
    """Render the budget tracker block."""
    budget_tracker_data = data_client.get_data(
        table_name="budget_tracker",
        query_string="id,name",
    )
    budget_tracker_map: dict[str, str] = {
        str(bt["id"]): str(bt["name"]) for bt in budget_tracker_data
    }
    budget_tracker_ids = list(budget_tracker_map.keys())

    def get_budget_tracker_name(bt_id: str | float) -> str:
        return budget_tracker_map.get(str(bt_id), "Unknown Budget Tracker")

    budget_tracker_tab, expense_tab, income_tab = st.tabs(
        ["Budget Tracker", "Expense Sources", "Income Sources"],
    )

    with budget_tracker_tab:
        base_block.render_dfe_tab(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_BUDGET_TRACKER_TABLE,
            ),
            backend_model=backend_models.BudgetTrackerItemModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn("🔠 Name", required=True),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="total_budget",
                    column_config=st.column_config.NumberColumn(
                        "💰 Total Budget",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Total Budget",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "💵 Current Month",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_BUDGET_TRACKER_SAMPLE_DATA,
            tables_to_clear=_BUDGET_TRACKER_TABLES_TO_CLEAR,
        )

    with expense_tab:
        base_block.render_dfe_tab(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_EXPENSE_SOURCES_TABLE,
                read_table=_EXPENSE_SOURCES_VIEW,
            ),
            backend_model=backend_models.ExpenseSourceModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn("🔠 Name", required=True),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="budget",
                    column_config=st.column_config.NumberColumn(
                        "💰 Budget",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Budget",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "📐 Split",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                    ),
                    button_label="Split",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "💵 Current Month",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "📊 Progress",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                        color="auto-inverse",
                    ),
                    button_label="Progress",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "💰 Remaining",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_EXPENSE_SOURCES_SAMPLE_DATA,
            tables_to_clear=_EXPENSE_SOURCES_TABLES_TO_CLEAR,
        )

    with income_tab:
        base_block.render_dfe_tab(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_INCOME_SOURCES_TABLE,
                read_table=_INCOME_SOURCES_VIEW,
            ),
            backend_model=backend_models.IncomeSourceModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn("🔠 Name", required=True),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "💵 Current Month",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="budget_tracker_ids",
                    column_config=st.column_config.MultiselectColumn(
                        "📋 Budget Trackers",
                        options=budget_tracker_ids,
                        format_func=get_budget_tracker_name,
                    ),
                    button_label="Budget Trackers",
                    input_widget=st.multiselect,
                    input_kwargs={
                        "options": budget_tracker_ids,
                        "format_func": get_budget_tracker_name,
                    },
                    format_func=get_budget_tracker_name,
                ),
            ],
            sample_data=_INCOME_SOURCES_SAMPLE_DATA,
            tables_to_clear=_INCOME_SOURCES_TABLES_TO_CLEAR,
        )
