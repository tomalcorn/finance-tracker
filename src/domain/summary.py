"""Headline figures derived from the dashboard's view read models.

Pure aggregation over ``read_models``: no ports, no framework, no display
formatting. The UI turns a :class:`DashboardSummary` into metric cards; the
arithmetic lives here so it is testable without Streamlit.
"""

import collections
import datetime
from typing import TYPE_CHECKING, Annotated

import pydantic

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models

HISTORY_MONTHS = 6

type _MonthKey = tuple[int, int]


class DashboardSummary(pydantic.BaseModel):
    """The headline figures for one dashboard page.

    The ``*_history`` series run oldest to newest and always end on the current
    month, so the last entry of each is the figure the matching headline field
    reports.
    """

    model_config = pydantic.ConfigDict(frozen=True)

    total_balance: Annotated[
        float,
        pydantic.Field(description="Combined current balance of every account."),
    ]
    balance_history: Annotated[
        tuple[float, ...],
        pydantic.Field(description="Combined balance at each month's end."),
    ]
    total_budget: Annotated[
        float,
        pydantic.Field(description="Combined budget of every budget tracker."),
    ]
    remaining_budget: Annotated[
        float,
        pydantic.Field(description="Combined budget left after this month's spend."),
    ]
    expenditure: Annotated[
        float,
        pydantic.Field(description="Expense payments dated in the current month."),
    ]
    expenditure_history: Annotated[
        tuple[float, ...],
        pydantic.Field(description="Expense payments totalled per month."),
    ]

    @property
    def expenditure_delta(self) -> float | None:
        """Return the change in expenditure against last month, if it is known."""
        if len(self.expenditure_history) < 2:  # noqa: PLR2004 — needs a prior month
            return None
        return self.expenditure - self.expenditure_history[-2]


def _month_key(day: datetime.date) -> _MonthKey:
    """Return the (year, month) a date falls in."""
    return (day.year, day.month)


def _trailing_months(today: datetime.date, months: int) -> list[_MonthKey]:
    """Return the ``months`` month keys ending on ``today``, oldest first."""
    year, month = today.year, today.month
    keys: list[_MonthKey] = []
    for _ in range(months):
        keys.append((year, month))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return list(reversed(keys))


def _totals_by_month(
    payments: "Sequence[read_models.PaymentView]",
) -> tuple[dict[_MonthKey, float], dict[_MonthKey, float]]:
    """Return per-month expense totals and per-month net movement."""
    expenses: dict[_MonthKey, float] = collections.defaultdict(float)
    nets: dict[_MonthKey, float] = collections.defaultdict(float)
    for payment in payments:
        key = _month_key(payment.payment_date)
        expenses[key] += payment.expense
        nets[key] += payment.income - payment.expense
    return expenses, nets


def _balance_history(
    total_balance: float,
    nets: dict[_MonthKey, float],
    keys: "Sequence[_MonthKey]",
) -> tuple[float, ...]:
    """Return the closing balance of each month, oldest first.

    Only the *current* balance is stored, so earlier months are reconstructed by
    walking backwards and undoing each month's net movement: the balance at the
    close of a month is the current balance less everything banked since.
    """
    running = total_balance
    balances: list[float] = []
    for key in reversed(keys):
        balances.append(running)
        running -= nets.get(key, 0.0)
    return tuple(reversed(balances))


def summarise(
    bank_accounts: "Sequence[read_models.BankAccountView]",
    budget_trackers: "Sequence[read_models.BudgetTrackerView]",
    payments: "Sequence[read_models.PaymentView]",
    today: datetime.date | None = None,
    months: int = HISTORY_MONTHS,
) -> DashboardSummary:
    """Summarise one dashboard's views into its headline figures.

    Args:
        bank_accounts: The page's bank account view rows.
        budget_trackers: The page's budget tracker view rows.
        payments: The page's payment rows, over their whole history — earlier
            months are what the trailing series are built from.
        today: The date the current month is taken from. Defaults to today.
        months: How many months each trailing series covers, current included.

    Returns:
        The figures for this page, unformatted.

    """
    today = today or datetime.datetime.now(tz=datetime.UTC).date()
    keys = _trailing_months(today, months)
    expenses, nets = _totals_by_month(payments)
    total_balance = sum(account.current_balance for account in bank_accounts)

    return DashboardSummary(
        total_balance=total_balance,
        balance_history=_balance_history(total_balance, nets, keys),
        total_budget=sum(tracker.total_budget for tracker in budget_trackers),
        remaining_budget=sum(tracker.remaining for tracker in budget_trackers),
        expenditure=expenses.get(_month_key(today), 0.0),
        expenditure_history=tuple(expenses.get(key, 0.0) for key in keys),
    )
