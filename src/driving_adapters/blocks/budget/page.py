"""The budget area's page: the master list, and the panel it drives.

The list runs income, then the allocation panel, then one entry per budget
tracker — the order the decisions happen in: what came in, how it is split,
then what each split is being spent on. Income and the panel are not siblings
of a tracker and the list does not pretend they are.
"""

import dataclasses
from typing import TYPE_CHECKING

import streamlit as st

from driving_adapters.blocks.budget import allocation, context, detail, grids
from driving_adapters.components.dfes import grid

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models
    from driving_adapters.models import frontend_models

INCOME_ENTRY = "income"

TRACKERS_ENTRY = "trackers"

SELECTED_KEY = "budget_area_selected"

MASTER_COLUMN_WIDTHS = [1.1, 5]


@dataclasses.dataclass(frozen=True)
class MasterEntry:
    """One row of the master list: what it is called, and where it stands."""

    key: str
    label: str
    sublabel: str
    icon: str | None


def master_entries(area: context.BudgetArea) -> list[MasterEntry]:
    """Build the master list."""
    roots = context.roots(area)
    allocated = sum(root.budget for root in roots)
    entries = [
        MasterEntry(
            INCOME_ENTRY,
            "Income",
            f"£{context.total_income(area):,.2f} in",
            ":material/add_circle:",
        ),
        MasterEntry(
            TRACKERS_ENTRY,
            "Budget trackers",
            f"£{allocated:,.2f} allocated",
            ":material/tune:",
        ),
    ]
    entries += [
        MasterEntry(
            str(root.id),
            str(root.name),
            f"£{root.remaining:,.2f} left",
            context.ROOT_ICONS.get(root.name),
        )
        for root in roots
    ]
    return entries


def selection(area: context.BudgetArea) -> str:
    """Read (and default) the master list's selection.

    Defaults to the first tracker rather than the first entry: income and the
    allocation panel are where a budget is set up, but the trackers are what
    the page is opened to look at day to day.
    """
    keys = [entry.key for entry in master_entries(area)]
    roots = context.roots(area)
    fallback = str(roots[0].id) if roots else INCOME_ENTRY
    current = st.session_state.get(SELECTED_KEY)
    if current not in keys:
        current = fallback
        st.session_state[SELECTED_KEY] = current
    return current


def selected_root(area: context.BudgetArea) -> "read_models.CategoryView | None":
    """Return the tracker the detail panel is showing, if it is showing one."""
    selected = selection(area)
    return next(
        (root for root in context.roots(area) if str(root.id) == selected),
        None,
    )


def configs(area: context.BudgetArea) -> list["frontend_models.DFEConfig"]:
    """Return the configs for whichever entry the detail panel is showing.

    Only the selected entry's grids: the panel renders one entry at a time, so
    no other grid has deltas waiting. An edit reruns the script with the
    selection unchanged, which is the run that commits it.
    """
    selected = selection(area)
    configs: list[frontend_models.DFEConfig] = []
    if selected == INCOME_ENTRY:
        configs.append(grids.income_config(area))
    elif selected != TRACKERS_ENTRY:
        root = selected_root(area)
        if root is not None and context.children_of(area, str(root.id)):
            configs.append(grids.children_config(area, root))
    return configs


def commit(area: context.BudgetArea) -> None:
    """Apply any pending backend updates for this block."""
    for config in configs(area):
        grid.commit(config)


def render_master(area: context.BudgetArea, entries: "Sequence[MasterEntry]") -> None:
    """Render the master list, one button per entry."""
    selected = selection(area)
    for entry in entries:
        if st.button(
            f"{entry.label}\n\n{entry.sublabel}",
            key=f"budget_area_pick_{entry.key}",
            type="primary" if entry.key == selected else "secondary",
            width="stretch",
            icon=entry.icon,
        ):
            st.session_state[SELECTED_KEY] = entry.key
            st.rerun()


def render_detail(area: context.BudgetArea) -> None:
    """Render the detail for whichever master-list entry is selected."""
    selected = selection(area)
    if selected == INCOME_ENTRY:
        st.markdown("##### :material/add_circle: Income sources")
        st.caption("What the budget trackers are split out of.")
        grid.render(grids.income_config(area))
        return
    if selected == TRACKERS_ENTRY:
        st.markdown("##### :material/tune: Budget trackers")
        allocation.render_panel(area)
        return
    root = selected_root(area)
    if root is None:
        st.info("No budget trackers yet.")
        return
    detail.render_tracker(area, root)


def render(area: context.BudgetArea) -> None:
    """Render the budget area: the master list, and the selected detail."""
    master_col, detail_col = st.columns(MASTER_COLUMN_WIDTHS, gap="medium")
    with master_col:
        render_master(area, master_entries(area))
    with detail_col:
        render_detail(area)
