"""Block for the budget tracker section."""

import dataclasses
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities, query
from driving_adapters.components.buttons import constants, filter_button
from driving_adapters.components.dfes import column_widths, grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

    from driving_adapters.components.buttons import (
        contribute_button as contribute_button_component,
    )
    from driving_adapters.components.dfes import data_source as data_source_mod


@dataclasses.dataclass(frozen=True)
class BudgetTrackerSources:
    """The three grid data sources behind this block's tabs.

    Bundled rather than threaded through each call: the tabs are three views of
    one budget, so every entry point here needs all three, and always the same
    three.
    """

    budget_trackers: "data_source_mod.GridDataSource"
    expense_sources: "data_source_mod.GridDataSource"
    income_sources: "data_source_mod.GridDataSource"


_BUDGET_TRACKER_TABLE = "budget_tracker"

_EXPENSE_SOURCES_TABLE = "expense_sources"

_INCOME_SOURCES_TABLE = "income_sources"

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

# The income roll-up column is one column showing one of two months, so it is
# labelled for whichever month the settings put it on. The underlying column is
# always `current_month` — the view moves its window, not its name.
_INCOME_COLUMN_LABELS: dict[entities.IncomeRollUpPeriod, str] = {
    entities.IncomeRollUpPeriod.CURRENT_MONTH: "Current Month",
    entities.IncomeRollUpPeriod.PREVIOUS_MONTH: "Previous Month",
}

_PREVIOUS_MONTH_HELP = (
    "Income is rolled up over the **previous** month, so this month's budget "
    "splits against last month's pay. Change this in "
    "[Settings](/settings)."
)


def _build_budget_tracker_config(
    data_source: "data_source_mod.GridDataSource",
) -> frontend_models.DFEConfig:
    """Build the grid config for the budget tracker tab."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_BUDGET_TRACKER_TABLE,
            data_source=data_source,
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        required=True,
                        disabled=True,
                        width=column_widths.NAME,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="total_budget",
                    column_config=st.column_config.NumberColumn(
                        "Budget",
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
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "Current Month",
                        format="£%.2f",
                        disabled=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "Remaining",
                        format="£%.2f",
                        disabled=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "Progress",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="auto-inverse",
                    ),
                    button_label="Progress",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "Split",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="blue",
                    ),
                    button_label="Split",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                    total=True,
                ),
            ],
            sample_data=_BUDGET_TRACKER_SAMPLE_DATA,
            num_rows="fixed",
        ),
    )


def _build_expense_sources_config(
    data_source: "data_source_mod.GridDataSource",
    expenses_bt_id: str | None,
) -> frontend_models.DFEConfig:
    """Build the grid config for the expense sources tab."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_EXPENSE_SOURCES_TABLE,
            data_source=data_source,
            # The tab only shows sources linked to the expenses budget tracker
            # (via the array_contains filter below), so a source added through
            # the dialog must be linked too — otherwise it saves but is filtered
            # out of view, appearing not to persist.
            extra_row_values=(
                {"budget_tracker_ids": [expenses_bt_id]} if expenses_bt_id else None
            ),
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
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
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "Current Month",
                        format="£%.2f",
                        disabled=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "Remaining",
                        format="£%.2f",
                        disabled=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "Progress",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="auto-inverse",
                    ),
                    button_label="Progress",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "Split",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="blue",
                    ),
                    button_label="Split",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                    total=True,
                ),
                *(
                    [
                        frontend_models.DFEColumnConfig(
                            editable=False,
                            column_name="budget_tracker_ids",
                            column_config={"disabled": True},
                            visible=False,
                            filters=query.Filters(array_contains=expenses_bt_id),
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


def _build_income_sources_config(
    data_source: "data_source_mod.GridDataSource",
    budget_tracker_ids: list[str],
    get_budget_tracker_name: "Callable[[str | float], str]",
    income_roll_up_period: entities.IncomeRollUpPeriod,
) -> frontend_models.DFEConfig:
    """Build the grid config for the income sources tab."""
    roll_up_label = _INCOME_COLUMN_LABELS[income_roll_up_period]
    # Quiet on the default: only a moved window needs explaining, so the tooltip
    # is attached to the column just for the previous-month case.
    roll_up_help = (
        _PREVIOUS_MONTH_HELP
        if income_roll_up_period is entities.IncomeRollUpPeriod.PREVIOUS_MONTH
        else None
    )
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_INCOME_SOURCES_TABLE,
            data_source=data_source,
        ),
        display=frontend_models.GridDisplay(
            columns=[
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
            sample_data=_INCOME_SOURCES_SAMPLE_DATA,
        ),
    )


def _configs(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
    income_roll_up_period: entities.IncomeRollUpPeriod,
) -> tuple[
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
    frontend_models.DFEConfig,
]:
    """Build the budget-tracker, expense-source, and income-source grid configs."""
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
        _build_budget_tracker_config(sources.budget_trackers),
        _build_expense_sources_config(sources.expense_sources, expenses_bt_id),
        _build_income_sources_config(
            sources.income_sources,
            budget_tracker_ids,
            get_budget_tracker_name,
            income_roll_up_period,
        ),
    )


def commit(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
    income_roll_up_period: entities.IncomeRollUpPeriod = (
        entities.IncomeRollUpPeriod.CURRENT_MONTH
    ),
) -> None:
    """Apply any pending backend updates for this block.

    The roll-up period only labels a read-only column, so it makes no difference
    to what is written here — it is taken so the configs this builds match the
    ones ``render`` builds, which is what keeps the editor's widget deltas
    lining up with the columns they came from.
    """
    bt_config, es_config, is_config = _configs(
        sources,
        budget_tracker_map,
        income_roll_up_period,
    )
    grid.commit(bt_config)
    grid.commit(es_config)
    grid.commit(is_config)


def _render_with_contribute(
    config: frontend_models.DFEConfig,
    contribute_button: "contribute_button_component.ContributeButton",
) -> None:
    """Render the budget tracker grid with the contribute button in its button row.

    The default ``grid.render`` would stack the button above the row, so this
    composes the row itself — the same seam the one-offs block uses for its
    "bank it" button. The grid is ``num_rows="fixed"``, so filter is the only
    built-in button to sit alongside.
    """
    filter_col, contribute_col, _ = st.columns(
        constants.FILTER_CONTRIBUTE_BUTTON_WIDTHS,
    )
    with filter_col:
        filter_button.render_filter_button(config.source, config.display)
    with contribute_col:
        contribute_button()
    grid.render_editor(
        config.display,
        config.key_prefix,
        grid.build_working_df(config),
    )


def render(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
    contribute_button: "contribute_button_component.ContributeButton | None" = None,
    income_roll_up_period: entities.IncomeRollUpPeriod = (
        entities.IncomeRollUpPeriod.CURRENT_MONTH
    ),
) -> None:
    """Render the budget tracker block.

    Args:
        sources: The grid data sources behind the three tabs.
        budget_tracker_map: ``{id: name}`` of the user's budget trackers.
        contribute_button: The personal→joint contribution button, rendered
            above the budget tracker grid. Passed only by the personal page for a
            user who belongs to a joint account; ``None`` (the joint page and
            non-members) hides it, since contributing funds joint from personal.
        income_roll_up_period: The month the income sources tab totals payments
            over, from this half's settings. The figures themselves are windowed
            by the view; this only tells the tab what to call the column and,
            when the window has been moved, to explain it via the column tooltip.

    """
    bt_config, es_config, is_config = _configs(
        sources,
        budget_tracker_map,
        income_roll_up_period,
    )

    budget_tracker_tab, expense_tab, income_tab = st.tabs(
        [
            f"{constants.TabIcons.BUDGET_TRACKER} Budget Tracker",
            f"{constants.TabIcons.EXPENSE} Expense Sources",
            f"{constants.TabIcons.INCOME} Income Sources",
        ],
    )

    with budget_tracker_tab:
        if contribute_button is None:
            grid.render(bt_config)
        else:
            _render_with_contribute(bt_config, contribute_button)

    with expense_tab:
        grid.render(es_config)

    with income_tab:
        grid.render(is_config)
