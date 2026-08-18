"""Block for the budget tracker section.

The first tab is the allocation panel: a card per budget tracker and the
allocation ring, the one place a tracker's monthly budget is set. The other two
are grids — the expense categories beneath the "Expenses" tracker, and the
income sources. The category grids are told apart by ``parent_id``, so each
carries its own ``row_predicate`` and widget-key prefix over the one slice
already fetched — a filtered read would be Path B and would need its own cache
key.
"""

import dataclasses
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities, query, read_models
from driving_adapters.components.buttons import constants
from driving_adapters.components.charts import allocation_ring
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
    """The grid data sources behind this block's tabs.

    Bundled rather than threaded through each call: the tabs are views of one
    budget, so every entry point here needs both, and always the same two. Two
    sources for three tabs — the budget tracker and expense category tabs are
    two levels of one category tree, and so one source.
    """

    categories: "data_source_mod.GridDataSource"
    income_sources: "data_source_mod.GridDataSource"


_CHILDREN_GRID_ID = "expense_categories"

_INCOME_SOURCES_GRID_ID = "income_sources"

_ALLOCATION_KEY_PREFIX = "budget_allocation"

_BUDGET_STEP = 10.0

# Name and share, the input, then the spend — widest first, so the tracker a
# card belongs to is what the eye lands on.
_CARD_COLUMN_WIDTHS = [3, 3, 2]

_PANEL_COLUMN_WIDTHS = [3, 2]

_EXPENSE_CATEGORIES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Expense Category"],
        "budget": [0],
        "accrued": [0],
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
    entities.IncomeRollUpPeriod.CURRENT_MONTH: "Received This Month",
    entities.IncomeRollUpPeriod.PREVIOUS_MONTH: "Received Last Month",
}

_PREVIOUS_MONTH_HELP = (
    "Income is rolled up over the **previous** month, so this month's budget "
    "splits against last month's pay. Change this in "
    "[Settings](/settings)."
)


def _expense_child_predicate(
    expenses_bt_id: str | None,
) -> "Callable[[read_models.CategoryView], bool]":
    """Return the predicate selecting the rows the expense categories tab shows.

    Children of the "Expenses" root. Without that root — a workspace the seed
    has never run against — it falls back to every category that is neither a
    root nor a pot, so a user's own row is never invisible.
    """

    def is_expense_child(row: "read_models.CategoryView") -> bool:
        if expenses_bt_id is None:
            return not row.is_root and not row.is_pot
        return str(row.parent_id) == expenses_bt_id

    return is_expense_child


def _build_expense_categories_config(
    data_source: "data_source_mod.GridDataSource",
    expenses_bt_id: str | None,
) -> frontend_models.DFEConfig:
    """Build the grid config for the expense categories tab."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_CHILDREN_GRID_ID,
            data_source=data_source,
            row_predicate=_expense_child_predicate(expenses_bt_id),
            # The tab only shows the children of the expenses root, so a
            # category added through the dialog must be parented there too —
            # otherwise it saves as a root and appears not to persist.
            extra_row_values=(
                {"parent_id": expenses_bt_id} if expenses_bt_id else None
            ),
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="Name of the expense category.",
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
                        help="What this expense category is allowed each month.",
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
                        help=(
                            "This expense category's budget as a share of the "
                            "Expenses budget tracker budget."
                        ),
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
                        help=(
                            "Payments booked against this expense category for a "
                            "given month."
                        ),
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
            ],
            sample_data=_EXPENSE_CATEGORIES_SAMPLE_DATA,
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
            grid_id=_INCOME_SOURCES_GRID_ID,
            data_source=data_source,
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
            sample_data=_INCOME_SOURCES_SAMPLE_DATA,
        ),
    )


def _configs(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
    income_roll_up_period: entities.IncomeRollUpPeriod,
) -> tuple[frontend_models.DFEConfig, frontend_models.DFEConfig]:
    """Build the expense-category and income-source configs.

    Two, not three: the budget trackers tab is the allocation panel, which
    writes a column patch straight through the port rather than through a grid.
    """
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
        _build_expense_categories_config(sources.categories, expenses_bt_id),
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
    es_config, is_config = _configs(
        sources,
        budget_tracker_map,
        income_roll_up_period,
    )
    grid.commit(es_config)
    grid.commit(is_config)


def _roots(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
) -> list["read_models.CategoryView"]:
    """Return the budget trackers, in the fixed display order of their names."""
    order = list(entities.BudgetTrackerName)
    roots = [
        row
        for row in sources.categories.rows()
        if isinstance(row, read_models.CategoryView)
        and row.is_root
        and str(row.id) in budget_tracker_map
    ]
    return sorted(
        roots,
        key=lambda row: order.index(row.name) if row.name in order else len(order),
    )


def _total_income(sources: BudgetTrackerSources) -> float:
    """Return what the tracker budgets are being split out of."""
    return sum(
        row.current_month
        for row in sources.income_sources.rows()
        if isinstance(row, read_models.IncomeSourceView)
    )


def _budget_input(
    sources: BudgetTrackerSources,
    root: "read_models.CategoryView",
) -> None:
    """Render one tracker's monthly budget as an editable number."""
    key = f"{_ALLOCATION_KEY_PREFIX}_budget_{root.id}"

    def save() -> None:
        sources.categories.apply_edits(
            {str(root.id): {"budget": float(st.session_state[key])}},
        )

    st.number_input(
        "Total budget",
        value=float(root.budget),
        min_value=0.0,
        step=_BUDGET_STEP,
        format="%.2f",
        key=key,
        on_change=save,
        label_visibility="collapsed",
    )


def _render_tracker_card(
    sources: BudgetTrackerSources,
    root: "read_models.CategoryView",
    income: float,
    colours: allocation_ring.Palette,
) -> None:
    """Render one tracker's allocation card.

    The swatch ties the card to its slice of the ring, which is why the ring
    carries no legend. It also puts the tracker's identity in text beside the
    colour, which the light palette needs: two of its four hues sit under 3:1
    against the surface.
    """
    share = (root.budget / income * 100) if income else 0.0
    with st.container(border=True):
        name_col, input_col, spend_col = st.columns(
            _CARD_COLUMN_WIDTHS,
            vertical_alignment="center",
        )
        with name_col:
            st.markdown(
                f'<span style="color:{colours.tracker(str(root.name))};'
                f'font-size:1.1em">&#9679;</span> <strong>{root.name}</strong><br>'
                f'<span style="opacity:0.6;font-size:0.85em">'
                f"{share:.1f}% of income</span>",
                unsafe_allow_html=True,
            )
        with input_col:
            _budget_input(sources, root)
        with spend_col:
            st.caption(
                f"£{root.accrued:,.2f} spent\n\n£{root.remaining:,.2f} left",
            )


def render_allocation_panel(
    sources: BudgetTrackerSources,
    budget_tracker_map: dict[str, str],
    contribute_button: "contribute_button_component.ContributeButton | None" = None,
) -> None:
    """Render the allocation panel: a card per tracker, and the ring.

    Deliberately not a grid. Splitting income between the trackers is one
    decision about one pot of money, and rows of a table read as unrelated
    edits.
    """
    # Above the empty-state check: contributing to the joint account is a
    # page-level action, not one of the panel's contents, so a workspace with no
    # trackers yet must not also lose the button.
    if contribute_button is not None:
        contribute_button()

    roots = _roots(sources, budget_tracker_map)
    if not roots:
        st.info("No budget trackers yet.")
        return

    st.caption(
        "Set what each tracker is allowed each month. The ring is your income, split.",
    )

    colours = allocation_ring.palette()
    income = _total_income(sources)
    cards_col, ring_col = st.columns(_PANEL_COLUMN_WIDTHS, gap="medium")
    with cards_col:
        for root in roots:
            _render_tracker_card(sources, root, income, colours)
    with ring_col:
        allocation_ring.render(roots, income, colours)


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
        sources: The data sources behind the three tabs.
        budget_tracker_map: ``{id: name}`` of the user's budget trackers.
        contribute_button: The personal→joint contribution button, rendered
            above the allocation panel. Passed only by the personal page for a
            user who belongs to a joint account; ``None`` (the joint page and
            non-members) hides it, since contributing funds joint from personal.
        income_roll_up_period: The month the income sources tab totals payments
            over, from this half's settings. The figures themselves are windowed
            by the view; this only tells the tab what to call the column and,
            when the window has been moved, to explain it via the column tooltip.

    """
    es_config, is_config = _configs(
        sources,
        budget_tracker_map,
        income_roll_up_period,
    )

    budget_tracker_tab, expense_tab, income_tab = st.tabs(
        [
            f"{constants.TabIcons.BUDGET_TRACKER} Budget Tracker",
            f"{constants.TabIcons.EXPENSE} Expense Categories",
            f"{constants.TabIcons.INCOME} Income Sources",
        ],
    )

    with budget_tracker_tab:
        render_allocation_panel(sources, budget_tracker_map, contribute_button)

    with expense_tab:
        grid.render(es_config)

    with income_tab:
        grid.render(is_config)
