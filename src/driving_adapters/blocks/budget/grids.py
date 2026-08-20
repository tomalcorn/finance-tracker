"""The grid configs behind the budget area's detail panels."""

from typing import TYPE_CHECKING

import streamlit as st

from domain import entities
from driving_adapters.blocks.budget import columns, context
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

    from domain import read_models

CHILDREN_GRID_PREFIX = "categories"

INCOME_SOURCES_GRID_ID = "income_sources"


def children_predicate(root_id: str) -> "Callable[[read_models.CategoryView], bool]":
    """Return the predicate selecting one tracker's subcategories."""

    def is_child(row: "read_models.CategoryView") -> bool:
        return not row.is_root and str(row.parent_id) == root_id

    return is_child


def children_config(
    area: context.BudgetArea,
    root: "read_models.CategoryView",
) -> frontend_models.DFEConfig:
    """Build the grid over one tracker's subcategories.

    Parent and accrual are derived from the tracker the grid hangs under, so a
    row added here lands where it is being shown. That is what gives every
    tracker a working add button, not just the one the grid used to be wired to.
    """
    pot = context.is_pot_root(root)
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=f"{CHILDREN_GRID_PREFIX}_{root.id}",
            data_source=area.sources.categories,
            row_predicate=children_predicate(str(root.id)),
            extra_row_values={
                "parent_id": str(root.id),
                "accrual": (
                    entities.AccrualPeriod.MULTI_MONTH
                    if pot
                    else entities.AccrualPeriod.MONTHLY
                ),
            },
        ),
        display=frontend_models.GridDisplay(
            columns=(
                columns.pot_child_columns() if pot else columns.monthly_child_columns()
            ),
            sample_data=columns.POT_SAMPLE_DATA if pot else columns.MONTHLY_SAMPLE_DATA,
        ),
    )


def income_config(area: context.BudgetArea) -> frontend_models.DFEConfig:
    """Build the grid over the income sources."""
    roll_up_label = columns.INCOME_COLUMN_LABELS[area.income_roll_up_period]
    # Quiet on the default: only a moved window needs explaining, so the tooltip
    # is attached to the column just for the previous-month case.
    roll_up_help = (
        columns.PREVIOUS_MONTH_HELP
        if area.income_roll_up_period is entities.IncomeRollUpPeriod.PREVIOUS_MONTH
        else None
    )
    budget_tracker_ids = list(area.budget_tracker_map.keys())

    def get_budget_tracker_name(bt_id: str | float) -> str:
        return area.budget_tracker_map.get(str(bt_id), "Unknown Budget Tracker")

    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=INCOME_SOURCES_GRID_ID,
            data_source=area.sources.income_sources,
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="Where the money comes from.",
                        required=True,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="budget_tracker_ids",
                    column_config=st.column_config.MultiselectColumn(
                        "Budget Trackers",
                        help="The Budget Trackers this income funds.",
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
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        roll_up_label,
                        format="£%.2f",
                        disabled=True,
                        help=roll_up_help,
                    ),
                    button_label=roll_up_label,
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=columns.INCOME_SOURCES_SAMPLE_DATA,
        ),
    )
