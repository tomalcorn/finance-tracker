"""One tracker's detail: its headline figures, then its subcategories."""

from typing import TYPE_CHECKING

import streamlit as st

from domain import entities
from driving_adapters.blocks.budget import context, grids
from driving_adapters.components.buttons import add_button, bank_button, filter_button
from driving_adapters.components.dfes import grid

if TYPE_CHECKING:
    from domain import read_models

NO_CHILDREN_CAPTION = "No subcategories yet. Add one to break this tracker down."

BUTTON_WIDTH = 0.05


def child_button_widths(*, adds: bool, pot: bool) -> list[float]:
    """Size the button row for however many buttons the tracker has earned."""
    buttons = 1 + int(adds) + int(pot)
    return [BUTTON_WIDTH] * buttons + [1.0 - buttons * BUTTON_WIDTH]


def render_children(
    area: context.BudgetArea,
    root: "read_models.CategoryView",
) -> None:
    """Render one tracker's subcategories, with the buttons that act on them.

    A tracker that is one pot of money shows nothing here. One that is meant to
    be broken down but has not been yet shows the add button and says so, rather
    than an empty grid falling back to sample data — example figures under a
    real tracker read as real money.

    Rows already under a tracker are always drawn, whichever kind it is, so a
    subcategory cannot be made invisible by the tracker it sits under.
    """
    adds = context.takes_subcategories(root)
    children = context.children_of(area, str(root.id))
    if not children:
        if adds:
            st.caption(NO_CHILDREN_CAPTION)
            config = grids.children_config(area, root)
            add_button.render_add_button(config.source, config.display)
        return

    config = grids.children_config(area, root)
    working_df = grid.build_working_df(config)
    pot = context.is_pot_root(root)
    button_cols = st.columns(child_button_widths(adds=adds, pot=pot))
    next_col = 0
    if adds:
        with button_cols[next_col]:
            add_button.render_add_button(config.source, config.display)
        next_col += 1
    with button_cols[next_col]:
        filter_button.render_filter_button(config.source, config.display)
    if pot:
        with button_cols[next_col + 1]:
            bank_button.BankButton(
                area.bank_one_offs_use_case,
                area.bank_account_map,
            )(context.bankable_pots(area))
    grid.render_editor(config.display, config.grid_id, working_df)


def render_tracker(
    area: context.BudgetArea,
    root: "read_models.CategoryView",
) -> None:
    """Render one tracker: its headline figures, then its subcategories."""
    st.markdown(f"##### {context.ROOT_ICONS.get(root.name, '')} {root.name}")
    budget_col, spent_col, left_col, used_col = st.columns(4)
    with budget_col:
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
    with used_col:
        st.metric("Budget used", f"{root.progress:.1f}%")

    if root.name == entities.BudgetTrackerName.JOINT and area.contribute_button:
        area.contribute_button()
    render_children(area, root)
