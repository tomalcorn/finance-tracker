"""Top-level summary block for the finance tracker app."""

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from use_cases import summarise_finances

# Applied to each card's value and to any numeric delta.
_MONEY = "£%,.2f"


def _budget_caption(figures: "summarise_finances.FinanceSummary") -> str:
    """Describe how much of the total budget is left.

    A string delta, so it is exempt from the numeric ``format`` above and
    carries its own.
    """
    if figures.total_budget <= 0:
        return "no budget set"
    share = figures.remaining_budget / figures.total_budget * 100
    return f"{share:.0f}% of £{figures.total_budget:,.2f}"


def _expenditure_delta(figures: "summarise_finances.FinanceSummary") -> float | None:
    """Return the month-on-month change in spend, if there is one to show.

    An unchanged (or unknown) figure returns ``None`` rather than zero: a delta
    of zero still draws an arrow, which reads as movement where there is none —
    most visibly on a workspace with no payments at all.
    """
    return figures.expenditure_delta or None


def render(figures: "summarise_finances.FinanceSummary") -> None:
    """Render the summary metric cards.

    Args:
        figures: The headline figures for the page.

    """
    # Only two of the three cards carry a chart, so each is stretched to the
    # row's height — left to size themselves the row comes out ragged.
    balance_col, budget_col, expenditure_col = st.columns(3)

    with balance_col:
        st.metric(
            label="Total Balance",
            value=figures.total_balance,
            format=_MONEY,
            chart_data=figures.balance_history,
            chart_type="area",
            help="Combined current balance across every bank account.",
            border=True,
            height="stretch",
        )

    with budget_col:
        st.metric(
            label="Remaining Budget",
            value=figures.remaining_budget,
            format=_MONEY,
            delta=_budget_caption(figures),
            delta_color="off",
            # A caption, not a movement — an arrow would imply one.
            delta_arrow="off",
            help="Every budget tracker's budget, less what it has spent this month.",
            border=True,
            height="stretch",
        )

    with expenditure_col:
        st.metric(
            label="Spent This Month",
            value=figures.expenditure,
            format=_MONEY,
            delta=_expenditure_delta(figures),
            # Inverse: spending more than last month is the unwelcome direction.
            delta_color="inverse",
            chart_data=figures.expenditure_history,
            chart_type="bar",
            help="Expense payments dated in the current calendar month.",
            border=True,
            height="stretch",
        )
