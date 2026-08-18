"""Block for the budget area: a master list, and one detail panel.

The list runs income, then the allocation panel, then one entry per budget
tracker — the order the decisions happen in: what came in, how it is split,
then what each split is being spent on. Income and the panel are not siblings
of a tracker and the list does not pretend they are.

Every grid here reads the one category slice the page already fetched and
narrows it with its own ``row_predicate`` and widget-key prefix. A filtered read
would be Path B and would need its own cache key.
"""

import dataclasses
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities, query, read_models
from driving_adapters.components.buttons import add_button, bank_button, filter_button
from driving_adapters.components.charts import allocation_ring
from driving_adapters.components.dfes import column_widths, grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from driving_adapters.components.buttons import (
        contribute_button as contribute_button_component,
    )
    from driving_adapters.components.dfes import data_source as data_source_mod
    from use_cases import bank_one_offs


@dataclasses.dataclass(frozen=True)
class BudgetTrackerSources:
    """The grid data sources behind the budget area.

    Two sources for every grid on the page: the trackers, their subcategories
    and any orphan are three slices of the one category tree, and income is the
    other.
    """

    categories: "data_source_mod.GridDataSource"
    income_sources: "data_source_mod.GridDataSource"


@dataclasses.dataclass(frozen=True)
class BudgetArea:
    """Everything the budget area needs to render itself."""

    sources: BudgetTrackerSources
    budget_tracker_map: dict[str, str]
    bank_account_map: dict[str, str]
    bank_one_offs_use_case: "bank_one_offs.BankOneOffsUseCase"
    income_roll_up_period: entities.IncomeRollUpPeriod = (
        entities.IncomeRollUpPeriod.CURRENT_MONTH
    )
    contribute_button: "contribute_button_component.ContributeButton | None" = None


_INCOME_ENTRY = "income"

_TRACKERS_ENTRY = "trackers"

_SELECTED_KEY = "budget_area_selected"

_INCOME_SOURCES_GRID_ID = "income_sources"

_ORPHANS_GRID_ID = "orphan_categories"

_ALLOCATION_KEY_PREFIX = "budget_allocation"

_BUDGET_STEP = 10.0

_CARD_COLUMN_WIDTHS = [3, 3, 4]

_PANEL_COLUMN_WIDTHS = [3, 2]

_MASTER_COLUMN_WIDTHS = [1.1, 5]

_PROGRESS_CEILING = 100.0

_ROOT_ICONS: dict[str, str] = {
    entities.BudgetTrackerName.EXPENSES: ":material/do_not_disturb_on:",
    entities.BudgetTrackerName.JOINT: ":material/group:",
    entities.BudgetTrackerName.ONE_OFFS: ":material/bubble_chart:",
    entities.BudgetTrackerName.SAVINGS: ":material/savings:",
}

_NO_CHILDREN_CAPTION: dict[str, str] = {
    entities.BudgetTrackerName.JOINT: (
        "Contributions to the joint account are set up on the Subscriptions "
        "block, or one-off via **Contribute**. Nothing to break down here."
    ),
}

_DEFAULT_NO_CHILDREN_CAPTION = (
    "No subcategories yet — this tracker is one pot of money. Add one to break it down."
)

_MONTHLY_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Category"],
        "budget": [0],
        "accrued": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)

_POT_SAMPLE_DATA = pd.DataFrame(
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


def _categories(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return every category the user owns, roots and children alike."""
    return [
        row
        for row in area.sources.categories.rows()
        if isinstance(row, read_models.CategoryView)
    ]


def _roots(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return the budget trackers, in the fixed display order of their names."""
    order = list(entities.BudgetTrackerName)
    return sorted(
        (row for row in _categories(area) if row.is_root),
        key=lambda row: order.index(row.name) if row.name in order else len(order),
    )


def _children_of(area: BudgetArea, root_id: str) -> list["read_models.CategoryView"]:
    """Return the subcategories sitting under one tracker."""
    return [
        row
        for row in _categories(area)
        if not row.is_root and str(row.parent_id) == root_id
    ]


def _orphans(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return subcategories whose parent is not one of the trackers."""
    root_ids = {str(root.id) for root in _roots(area)}
    return [
        row
        for row in _categories(area)
        if not row.is_root and str(row.parent_id) not in root_ids
    ]


def _total_income(area: BudgetArea) -> float:
    """Return what the tracker budgets are being split out of."""
    return sum(
        row.current_month
        for row in area.sources.income_sources.rows()
        if isinstance(row, read_models.IncomeSourceView)
    )


def _is_pot_root(root: "read_models.CategoryView") -> bool:
    """Whether this tracker's subcategories are pots rather than monthly."""
    return root.name == entities.BudgetTrackerName.ONE_OFFS


def _monthly_child_columns() -> list[frontend_models.DFEColumnConfig]:
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


def _pot_child_columns() -> list[frontend_models.DFEColumnConfig]:
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
                "Share of Budget",
                help="The planned spend as a share of the One-offs budget.",
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


def _children_predicate(root_id: str) -> "Callable[[read_models.CategoryView], bool]":
    """Return the predicate selecting one tracker's subcategories."""

    def is_child(row: "read_models.CategoryView") -> bool:
        return not row.is_root and str(row.parent_id) == root_id

    return is_child


def _children_config(
    area: BudgetArea,
    root: "read_models.CategoryView",
) -> frontend_models.DFEConfig:
    """Build the grid over one tracker's subcategories.

    Parent and accrual are derived from the tracker the grid hangs under, so a
    row added here lands where it is being shown. That is what gives every
    tracker a working add button, not just the one the grid used to be wired to.
    """
    pot = _is_pot_root(root)
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=f"categories_{root.id}",
            data_source=area.sources.categories,
            row_predicate=_children_predicate(str(root.id)),
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
            columns=_pot_child_columns() if pot else _monthly_child_columns(),
            sample_data=_POT_SAMPLE_DATA if pot else _MONTHLY_SAMPLE_DATA,
        ),
    )


def _orphans_config(area: BudgetArea) -> frontend_models.DFEConfig:
    """Build the grid over subcategories that sit under no tracker."""
    orphan_ids = {str(row.id) for row in _orphans(area)}

    def is_orphan(row: "read_models.CategoryView") -> bool:
        return str(row.id) in orphan_ids

    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_ORPHANS_GRID_ID,
            data_source=area.sources.categories,
            row_predicate=is_orphan,
        ),
        display=frontend_models.GridDisplay(
            columns=_monthly_child_columns(),
            sample_data=_MONTHLY_SAMPLE_DATA,
        ),
    )


def _income_config(area: BudgetArea) -> frontend_models.DFEConfig:
    """Build the grid over the income sources."""
    roll_up_label = _INCOME_COLUMN_LABELS[area.income_roll_up_period]
    # Quiet on the default: only a moved window needs explaining, so the tooltip
    # is attached to the column just for the previous-month case.
    roll_up_help = (
        _PREVIOUS_MONTH_HELP
        if area.income_roll_up_period is entities.IncomeRollUpPeriod.PREVIOUS_MONTH
        else None
    )
    budget_tracker_ids = list(area.budget_tracker_map.keys())

    def get_budget_tracker_name(bt_id: str | float) -> str:
        return area.budget_tracker_map.get(str(bt_id), "Unknown Budget Tracker")

    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_INCOME_SOURCES_GRID_ID,
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
            sample_data=_INCOME_SOURCES_SAMPLE_DATA,
        ),
    )


@dataclasses.dataclass(frozen=True)
class _MasterEntry:
    """One row of the master list: what it is called, and where it stands."""

    key: str
    label: str
    sublabel: str
    icon: str | None


def _master_entries(area: BudgetArea) -> list[_MasterEntry]:
    """Build the master list."""
    roots = _roots(area)
    allocated = sum(root.budget for root in roots)
    entries = [
        _MasterEntry(
            _INCOME_ENTRY,
            "Income",
            f"£{_total_income(area):,.2f} in",
            ":material/add_circle:",
        ),
        _MasterEntry(
            _TRACKERS_ENTRY,
            "Budget trackers",
            f"£{allocated:,.2f} allocated",
            ":material/tune:",
        ),
    ]
    entries += [
        _MasterEntry(
            str(root.id),
            str(root.name),
            f"£{root.remaining:,.2f} left",
            _ROOT_ICONS.get(root.name),
        )
        for root in roots
    ]
    return entries


def _selection(area: BudgetArea) -> str:
    """Read (and default) the master list's selection.

    Defaults to the first tracker rather than the first entry: income and the
    allocation panel are where a budget is set up, but the trackers are what
    the page is opened to look at day to day.
    """
    keys = [entry.key for entry in _master_entries(area)]
    roots = _roots(area)
    fallback = str(roots[0].id) if roots else _INCOME_ENTRY
    current = st.session_state.get(_SELECTED_KEY)
    if current not in keys:
        current = fallback
        st.session_state[_SELECTED_KEY] = current
    return current


def _selected_root(area: BudgetArea) -> "read_models.CategoryView | None":
    """Return the tracker the detail panel is showing, if it is showing one."""
    selected = _selection(area)
    return next((root for root in _roots(area) if str(root.id) == selected), None)


def _configs(area: BudgetArea) -> list[frontend_models.DFEConfig]:
    """Return the configs for whichever entry the detail panel is showing.

    Only the selected entry's grids: the panel renders one entry at a time, so
    no other grid has deltas waiting. An edit reruns the script with the
    selection unchanged, which is the run that commits it.
    """
    selected = _selection(area)
    configs: list[frontend_models.DFEConfig] = []
    if selected == _INCOME_ENTRY:
        configs.append(_income_config(area))
    elif selected != _TRACKERS_ENTRY:
        root = _selected_root(area)
        if root is not None and _children_of(area, str(root.id)):
            configs.append(_children_config(area, root))
    if _orphans(area):
        configs.append(_orphans_config(area))
    return configs


def commit(area: BudgetArea) -> None:
    """Apply any pending backend updates for this block."""
    for config in _configs(area):
        grid.commit(config)


def _budget_input(area: BudgetArea, root: "read_models.CategoryView") -> None:
    """Render one tracker's monthly budget as an editable number."""
    key = f"{_ALLOCATION_KEY_PREFIX}_budget_{root.id}"

    def save() -> None:
        area.sources.categories.apply_edits(
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
    area: BudgetArea,
    root: "read_models.CategoryView",
    colours: allocation_ring.Palette,
) -> None:
    """Render one tracker's allocation card.

    The swatch ties the card to its slice of the ring, which is why the ring
    carries no legend. It also puts the tracker's identity in text beside the
    colour, which the light palette needs: two of its four hues sit under 3:1
    against the surface.
    """
    with st.container(border=True):
        name_col, input_col, spend_col = st.columns(
            _CARD_COLUMN_WIDTHS,
            vertical_alignment="center",
        )
        with name_col:
            st.markdown(
                f'<span style="color:{colours.tracker(str(root.name))}">&#9679;</span> '
                f"<strong>{root.name}</strong>",
                unsafe_allow_html=True,
            )
        with input_col:
            _budget_input(area, root)
        with spend_col:
            st.caption(f"£{root.accrued:,.2f} spent · £{root.remaining:,.2f} left")


def render_allocation_panel(area: BudgetArea) -> None:
    """Render the allocation panel: a card per tracker, and the ring.

    Deliberately not a grid. Splitting income between the trackers is one
    decision about one pot of money, and rows of a table read as unrelated
    edits.
    """
    roots = _roots(area)
    if not roots:
        st.info("No budget trackers yet.")
        return

    st.caption(
        "Set what each tracker is allowed each month. The ring is your income, split.",
    )
    colours = allocation_ring.palette()
    cards_col, ring_col = st.columns(_PANEL_COLUMN_WIDTHS, gap="medium")
    with cards_col:
        for root in roots:
            _render_tracker_card(area, root, colours)
    with ring_col:
        allocation_ring.render(roots, _total_income(area), colours)


def _bankable_pots(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return the pots with an amount planned for the current month.

    Read through the port rather than off the grid's display frame: banking acts
    on the aggregate, so neither an active column filter nor the sample data an
    empty frame falls back to gets to decide what is bankable.
    """
    return [row for row in _categories(area) if row.is_pot and row.budget > 0]


def _render_children(area: BudgetArea, root: "read_models.CategoryView") -> None:
    """Render one tracker's subcategories, with the buttons that act on them.

    With no subcategories the grid is left out entirely rather than falling back
    to sample data: example figures under a real tracker read as real money. The
    add button stays, so a tracker that has none can gain one.
    """
    config = _children_config(area, root)
    if not _children_of(area, str(root.id)):
        st.caption(
            _NO_CHILDREN_CAPTION.get(root.name, _DEFAULT_NO_CHILDREN_CAPTION),
        )
        add_button.render_add_button(config.source, config.display)
        return

    working_df = grid.build_working_df(config)
    pot = _is_pot_root(root)
    button_widths = [0.05, 0.05, 0.05, 0.85] if pot else [0.05, 0.05, 0.9]
    button_cols = st.columns(button_widths)
    with button_cols[0]:
        add_button.render_add_button(config.source, config.display)
    with button_cols[1]:
        filter_button.render_filter_button(config.source, config.display)
    if pot:
        with button_cols[2]:
            bank_button.BankButton(
                area.bank_one_offs_use_case,
                area.bank_account_map,
            )(_bankable_pots(area))
    grid.render_editor(config.display, config.grid_id, working_df)


def _render_root_detail(area: BudgetArea, root: "read_models.CategoryView") -> None:
    """Render one tracker: its headline figures, then its subcategories."""
    st.markdown(
        f"##### {root.name} · £{root.accrued:,.2f} of £{root.budget:,.2f} "
        f"· £{root.remaining:,.2f} left",
    )
    budget_col, spent_col, left_col, share_col = st.columns(4)
    with budget_col:
        # Read-only: a tracker's budget has one home, the allocation panel.
        st.metric("Total budget", f"£{root.budget:,.2f}")
    with spent_col:
        st.metric("Spent", f"£{root.accrued:,.2f}")
    with left_col:
        st.metric(
            "Remaining",
            f"£{root.remaining:,.2f}",
            delta=None if root.remaining >= 0 else "over budget",
            delta_color="inverse",
        )
    with share_col:
        st.metric("Share of income", f"{root.split:.1f}%")
    st.progress(min(max(root.progress, 0.0), _PROGRESS_CEILING) / _PROGRESS_CEILING)

    if root.name == entities.BudgetTrackerName.JOINT and area.contribute_button:
        area.contribute_button()
    _render_children(area, root)


def _render_orphans(area: BudgetArea) -> None:
    """Render any subcategory whose parent is not one of the trackers.

    A no-op in a healthy workspace. It exists because the detail panel only ever
    draws children underneath their tracker, and a row with no tracker to sit
    under would otherwise vanish from the page altogether.
    """
    orphans = _orphans(area)
    if not orphans:
        return
    one = len(orphans) == 1
    st.warning(
        f"{len(orphans)} categor{'y' if one else 'ies'} "
        f"{'sits' if one else 'sit'} under no budget tracker.",
        icon=":material/warning:",
    )
    grid.render(_orphans_config(area))


def _render_master(area: BudgetArea, entries: "Sequence[_MasterEntry]") -> None:
    """Render the master list, one button per entry."""
    selected = _selection(area)
    for entry in entries:
        if st.button(
            f"{entry.label}\n\n{entry.sublabel}",
            key=f"budget_area_pick_{entry.key}",
            type="primary" if entry.key == selected else "secondary",
            width="stretch",
            icon=entry.icon,
        ):
            st.session_state[_SELECTED_KEY] = entry.key
            st.rerun()


def _render_detail(area: BudgetArea) -> None:
    """Render the detail for whichever master-list entry is selected."""
    selected = _selection(area)
    if selected == _INCOME_ENTRY:
        st.markdown("##### :material/add_circle: Income sources")
        st.caption("What the budget trackers are split out of.")
        grid.render(_income_config(area))
        return
    if selected == _TRACKERS_ENTRY:
        st.markdown("##### :material/tune: Budget trackers")
        render_allocation_panel(area)
        return
    root = _selected_root(area)
    if root is None:
        st.info("No budget trackers yet.")
        return
    _render_root_detail(area, root)


def render(area: BudgetArea) -> None:
    """Render the budget area: the master list, and the selected detail."""
    master_col, detail_col = st.columns(_MASTER_COLUMN_WIDTHS, gap="medium")
    with master_col:
        _render_master(area, _master_entries(area))
    with detail_col:
        _render_detail(area)
    _render_orphans(area)
