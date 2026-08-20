"""The allocation panel: a card per tracker, and the ring beside them.

Deliberately not a grid. Splitting income between the trackers is one decision
about one pot of money, and rows of a table read as unrelated edits.
"""

from typing import TYPE_CHECKING

import streamlit as st

from driving_adapters.blocks.budget import context
from driving_adapters.components.charts import allocation_ring

if TYPE_CHECKING:
    from domain import read_models

ALLOCATION_KEY_PREFIX = "budget_allocation"

BUDGET_STEP = 10.0

CARD_COLUMN_WIDTHS = [3, 3, 4]

PANEL_COLUMN_WIDTHS = [3, 2]


def budget_input(area: context.BudgetArea, root: "read_models.CategoryView") -> None:
    """Render one tracker's monthly budget as an editable number."""
    key = f"{ALLOCATION_KEY_PREFIX}_budget_{root.id}"

    def save() -> None:
        area.sources.categories.apply_edits(
            {str(root.id): {"budget": float(st.session_state[key])}},
        )

    st.number_input(
        "Total budget",
        value=float(root.budget),
        min_value=0.0,
        step=BUDGET_STEP,
        format="%.2f",
        key=key,
        on_change=save,
        label_visibility="collapsed",
    )


def render_tracker_card(
    area: context.BudgetArea,
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
            CARD_COLUMN_WIDTHS,
            vertical_alignment="center",
        )
        with name_col:
            st.markdown(
                f'<span style="color:{colours.tracker(str(root.name))}">&#9679;</span> '
                f"<strong>{root.name}</strong>",
                unsafe_allow_html=True,
            )
        with input_col:
            budget_input(area, root)
        with spend_col:
            st.caption(f"£{root.accrued:,.2f} spent · £{root.remaining:,.2f} left")


def render_panel(area: context.BudgetArea) -> None:
    """Render the allocation panel: a card per tracker, and the ring.

    Deliberately not a grid. Splitting income between the trackers is one
    decision about one pot of money, and rows of a table read as unrelated
    edits.
    """
    roots = context.roots(area)
    if not roots:
        st.info("No budget trackers yet.")
        return

    st.caption(
        "Set what each tracker is allowed each month. The ring is your income, split.",
    )
    colours = allocation_ring.palette()
    cards_col, ring_col = st.columns(PANEL_COLUMN_WIDTHS, gap="medium")
    with cards_col:
        for root in roots:
            render_tracker_card(area, root, colours)
    with ring_col:
        allocation_ring.render(roots, context.total_income(area), colours)
