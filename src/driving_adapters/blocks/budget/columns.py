"""The column sets the budget area's grids are built from."""

import pandas as pd
import streamlit as st

from domain import entities, query
from driving_adapters.components.dfes import column_widths
from driving_adapters.models import frontend_models

MONTHLY_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Category"],
        "budget": [0],
        "accrued": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)

POT_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example One-Off"],
        "cost": [0],
        "budget": [0],
        "starting_balance": [0],
        "accrued": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)

INCOME_SOURCES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Income Source"],
        "current_month": [0],
        "budget_tracker_ids": [[]],
    },
)

# The income roll-up column is one column showing one of two months, so it is
# labelled for whichever month the settings put it on. The underlying column is
# always `current_month` — the view moves its window, not its name.
INCOME_COLUMN_LABELS: dict[entities.IncomeRollUpPeriod, str] = {
    entities.IncomeRollUpPeriod.CURRENT_MONTH: "Received This Month",
    entities.IncomeRollUpPeriod.PREVIOUS_MONTH: "Received Last Month",
}

PREVIOUS_MONTH_HELP = (
    "Income is rolled up over the **previous** month, so this month's budget "
    "splits against last month's pay. Change this in "
    "[Settings](/settings)."
)


def monthly_child_columns() -> list[frontend_models.DFEColumnConfig]:
    """Build the column set for a subcategory that resets each month."""
    return [
        frontend_models.DFEColumnConfig(
            column_name="name",
            column_config=st.column_config.TextColumn(
                "Name",
                help="Name of the category.",
                required=True,
                width=column_widths.NAME,
            ),
            button_label="Name",
            input_widget=st.text_input,
            input_kwargs={"value": None},
        ),
        frontend_models.DFEColumnConfig(
            column_name="budget",
            column_config=st.column_config.NumberColumn(
                "Budget",
                help="What this category is allowed each month.",
                format="£%.2f",
                required=True,
                width=column_widths.MONEY,
            ),
            button_label="Budget",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            sorting=query.SortingValues.DESC,
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="split",
            column_config=st.column_config.ProgressColumn(
                "Share of Budget",
                help="This category's budget as a share of its tracker's.",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width=column_widths.PROGRESS,
                color="blue",
            ),
            button_label="Share of Budget",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.1f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="accrued",
            column_config=st.column_config.NumberColumn(
                "Spent",
                help="Payments booked against this category for a given month.",
                format="£%.2f",
                disabled=True,
                width=column_widths.MONEY,
            ),
            button_label="Spent",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="progress",
            column_config=st.column_config.ProgressColumn(
                "% Spent",
                help="How much of the budget is gone.",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width=column_widths.PROGRESS,
                color="auto-inverse",
            ),
            button_label="% Spent",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.1f"},
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="remaining",
            column_config=st.column_config.NumberColumn(
                "Remaining",
                help="Left to spend this month.",
                format="£%.2f",
                disabled=True,
                width=column_widths.MONEY,
            ),
            button_label="Remaining",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            total=True,
        ),
    ]


def pot_child_columns() -> list[frontend_models.DFEColumnConfig]:
    """Build the column set for a pot, which fills up across months."""
    return [
        frontend_models.DFEColumnConfig(
            column_name="name",
            column_config=st.column_config.TextColumn(
                "Name",
                help="What you are saving up for.",
                required=True,
                width=column_widths.NAME,
            ),
            button_label="Name",
            input_widget=st.text_input,
            input_kwargs={"value": None},
        ),
        frontend_models.DFEColumnConfig(
            column_name="cost",
            column_config=st.column_config.NumberColumn(
                "Cost",
                help="What the item costs in total.",
                format="£%.2f",
                required=True,
                width=column_widths.MONEY,
            ),
            button_label="Cost",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            column_name="budget",
            column_config=st.column_config.NumberColumn(
                "Planned",
                help="What you intend to put towards it this month.",
                format="£%.2f",
                required=True,
                width=column_widths.MONEY,
            ),
            button_label="Planned",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="split",
            column_config=st.column_config.ProgressColumn(
                "Share of Remaining",
                help=(
                    "The planned spend as a share of what the One-offs budget "
                    "has left to allocate this month. Reads 0% once nothing is "
                    "left."
                ),
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width=column_widths.PROGRESS,
                color="blue",
            ),
            button_label="Share of Remaining",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.1f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            column_name="starting_balance",
            column_config=st.column_config.NumberColumn(
                "Starting",
                help=(
                    "What the pot held before payments could reach it. "
                    "Edit it to move money in or out by hand."
                ),
                format="£%.2f",
                required=True,
                width=column_widths.MONEY,
            ),
            button_label="Starting",
            input_widget=st.number_input,
            input_kwargs={"value": 0.0, "format": "%.2f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="accrued",
            column_config=st.column_config.NumberColumn(
                "Spent/Banked",
                help=(
                    "Computed: the starting balance plus every payment "
                    "attributed to this pot."
                ),
                format="£%.2f",
                disabled=True,
                width=column_widths.MONEY,
            ),
            button_label="Spent/Banked",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
            total=True,
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="progress",
            column_config=st.column_config.ProgressColumn(
                "% Spent/Banked",
                help="How much of the cost you have banked.",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width=column_widths.PROGRESS,
                color="blue",
            ),
            button_label="% Spent/Banked",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.1f"},
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
            column_name="remaining",
            column_config=st.column_config.NumberColumn(
                "Remaining",
                help="The amount of the cost still left to bank.",
                format="£%.2f",
                disabled=True,
                width=column_widths.MONEY,
            ),
            button_label="Remaining",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
        ),
    ]
