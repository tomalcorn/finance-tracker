"""Block for the budget tracker section."""

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities, query
from ui import data_client
from ui.components.buttons import constants
from ui.components.dfes import base_dfe
from ui.models import frontend_models

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


def _build_budget_tracker_dfe() -> base_dfe.DFE:
    """Build the DFE for the budget tracker tab."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
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
        ),
    )


def _build_expense_sources_dfe(expenses_bt_id: str | None) -> base_dfe.DFE:
    """Build the DFE for the expense sources tab."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
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
        ),
    )


def _build_income_sources_dfe(
    budget_tracker_ids: list[str],
    get_budget_tracker_name: "Callable",
) -> base_dfe.DFE:
    """Build the DFE for the income sources tab."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
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
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_BUDGET_TRACKER_TABLE,
        key_prefix=_BUDGET_TRACKER_TABLE,
    )
    data_client.commit(
        table_name=_EXPENSE_SOURCES_TABLE,
        key_prefix=_EXPENSE_SOURCES_TABLE,
    )
    data_client.commit(
        table_name=_INCOME_SOURCES_TABLE,
        key_prefix=_INCOME_SOURCES_TABLE,
    )


def render() -> None:
    """Render the budget tracker block."""
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

    budget_tracker_tab, expense_tab, income_tab = st.tabs(
        [
            f"{constants.TabIcons.BUDGET_TRACKER} Budget Tracker",
            f"{constants.TabIcons.EXPENSE} Expense Sources",
            f"{constants.TabIcons.INCOME} Income Sources",
        ],
    )

    with budget_tracker_tab:
        bt_dfe = _build_budget_tracker_dfe()
        bt_dfe.load_input_data()
        data_added, filters_changed = bt_dfe.render_buttons()
        bt_dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        bt_dfe.render_editor()

    with expense_tab:
        es_dfe = _build_expense_sources_dfe(expenses_bt_id)
        es_dfe.load_input_data()
        data_added, filters_changed = es_dfe.render_buttons()
        es_dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        es_dfe.render_editor()

    with income_tab:
        is_dfe = _build_income_sources_dfe(budget_tracker_ids, get_budget_tracker_name)
        is_dfe.load_input_data()
        data_added, filters_changed = is_dfe.render_buttons()
        is_dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        is_dfe.render_editor()
