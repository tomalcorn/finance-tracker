"""Block for the budget tracker section."""

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities, query
from driving_adapters.components.buttons import constants
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

_BUDGET_TRACKER_TABLE = "budget_tracker"
_BUDGET_TRACKER_VIEW = "budget_tracker_view"

_EXPENSE_SOURCES_TABLE = "expense_sources"
_EXPENSE_SOURCES_VIEW = "expense_sources_view"

_INCOME_SOURCES_TABLE = "income_sources"
_INCOME_SOURCES_VIEW = "income_sources_view"

_BUDGET_TRACKER_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Budget Tracker"],
        "total_budget": [0],
        "current_month": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)

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


def _build_budget_tracker_config() -> frontend_models.DFEConfig:
    """Build the grid config for the budget tracker tab."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_BUDGET_TRACKER_TABLE,
            read_table=_BUDGET_TRACKER_VIEW,
        ),
        data_source=wiring.budget_tracker_data_source(),
        read_via_repository=True,
        backend_model=entities.BudgetTrackerItemModel,
        configs=[
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="name",
                column_config=st.column_config.TextColumn(
                    "Name",
                    required=True,
                    disabled=True,
                ),
                button_label="Name",
                input_widget=st.text_input,
                input_kwargs={"value": None},
            ),
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="split",
                column_config=st.column_config.ProgressColumn(
                    "Split",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    color="blue",
                ),
                button_label="Split",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.1f"},
            ),
            frontend_models.DFEColumnConfig(
                column_name="total_budget",
                column_config=st.column_config.NumberColumn(
                    "Budget",
                    format="£%.2f",
                    required=True,
                ),
                button_label="Budget",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="current_month",
                column_config=st.column_config.NumberColumn(
                    "Current Month",
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
                    "Progress",
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
                    "Remaining",
                    format="£%.2f",
                    disabled=True,
                ),
                button_label="Remaining",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
        ],
        sample_data=_BUDGET_TRACKER_SAMPLE_DATA,
        num_rows="fixed",
    )


def _build_expense_sources_config(
    expenses_bt_id: str | None,
) -> frontend_models.DFEConfig:
    """Build the grid config for the expense sources tab."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_EXPENSE_SOURCES_TABLE,
            read_table=_EXPENSE_SOURCES_VIEW,
        ),
        data_source=wiring.expense_source_data_source(),
        read_via_repository=True,
        backend_model=entities.ExpenseSourceModel,
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
                column_name="budget",
                column_config=st.column_config.NumberColumn(
                    "Budget",
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
                    "Split",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    color="blue",
                ),
                button_label="Split",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.1f"},
            ),
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="current_month",
                column_config=st.column_config.NumberColumn(
                    "Current Month",
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
                    "Progress",
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
                    "Remaining",
                    format="£%.2f",
                    disabled=True,
                ),
                button_label="Remaining",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            *(
                [
                    frontend_models.DFEReadOnlyColumnConfig(
                        column_name="budget_tracker_ids",
                        column_config={"disabled": True},
                        visible=False,
                        filters=query.Filters(cs=expenses_bt_id),
                        input_widget=st.text_input,
                    ),
                ]
                if expenses_bt_id
                else []
            ),
        ],
        sample_data=_EXPENSE_SOURCES_SAMPLE_DATA,
    )


def _build_income_sources_config(
    budget_tracker_ids: list[str],
    get_budget_tracker_name: "Callable[[str | float], str]",
) -> frontend_models.DFEConfig:
    """Build the grid config for the income sources tab."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_INCOME_SOURCES_TABLE,
            read_table=_INCOME_SOURCES_VIEW,
        ),
        data_source=wiring.income_source_data_source(),
        read_via_repository=True,
        backend_model=entities.IncomeSourceModel,
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
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="current_month",
                column_config=st.column_config.NumberColumn(
                    "Current Month",
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
                    "Budget Trackers",
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
    )


def _configs() -> tuple[
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
]:
    """Build the budget-tracker, expense-source, and income-source grid configs."""
    budget_tracker_map = wiring.budget_tracker_id_name_map()
    budget_tracker_ids = list(budget_tracker_map.keys())

    expenses_bt_id = next(
        (
            bt_id
            for bt_id, name in budget_tracker_map.items()
            if name == entities.BudgetTrackerName.EXPENSES
        ),
        None,
    )

    def get_budget_tracker_name(bt_id: str | float) -> str:
        return budget_tracker_map.get(str(bt_id), "Unknown Budget Tracker")

    return (
        _build_budget_tracker_config(),
        _build_expense_sources_config(expenses_bt_id),
        _build_income_sources_config(budget_tracker_ids, get_budget_tracker_name),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    bt_config, es_config, is_config = _configs()
    grid.commit(bt_config)
    grid.commit(es_config)
    grid.commit(is_config)


def render() -> None:
    """Render the budget tracker block."""
    bt_config, es_config, is_config = _configs()

    budget_tracker_tab, expense_tab, income_tab = st.tabs(
        [
            f"{constants.TabIcons.BUDGET_TRACKER} Budget Tracker",
            f"{constants.TabIcons.EXPENSE} Expense Sources",
            f"{constants.TabIcons.INCOME} Income Sources",
        ],
    )

    with budget_tracker_tab:
        grid.render(bt_config)

    with expense_tab:
        grid.render(es_config)

    with income_tab:
        grid.render(is_config)
