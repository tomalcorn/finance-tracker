"""Use-case producing the headline figures shown above a dashboard page."""

import collections
import datetime
from typing import TYPE_CHECKING, Annotated

import pydantic

from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models
    from ports import views

HISTORY_MONTHS = 6

# A change is only meaningful once a month has one to be compared against.
_MONTHS_NEEDED_FOR_A_DELTA = 2

type _MonthKey = tuple[int, int]


class FinanceSummary(pydantic.BaseModel):
    """The headline figures for one set of accounts.

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
        list[float],
        pydantic.Field(description="Combined balance at each month's end."),
    ]
    total_budget: Annotated[
        float,
        pydantic.Field(description="Combined budget of every root category."),
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
        list[float],
        pydantic.Field(description="Expense payments totalled per month."),
    ]

    @property
    def expenditure_delta(self) -> float | None:
        """Return the change in expenditure against last month, if it is known."""
        if len(self.expenditure_history) < _MONTHS_NEEDED_FOR_A_DELTA:
            return None
        return self.expenditure - self.expenditure_history[-2]


def _today() -> datetime.date:
    """Return the current UTC date.

    Deliberately read per call rather than fixed at import: the app process
    outlives a day, and a stale date would report the wrong month's figures
    until it restarted.
    """
    return datetime.datetime.now(tz=datetime.UTC).date()


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
) -> list[float]:
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
    return list(reversed(balances))


class SummariseFinancesUseCase:
    """Use-case for folding one page's view rows into its headline figures."""

    def __init__(
        self,
        bank_account_source: "views.ViewSource[read_models.BankAccountView]",
        category_source: "views.ViewSource[read_models.CategoryView]",
        payment_source: "views.ViewSource[read_models.PaymentView]",
        today: datetime.date | None = None,
        months: int = HISTORY_MONTHS,
    ) -> None:
        """Construct SummariseFinancesUseCase.

        Args:
            bank_account_source: Reads the bank account view rows.
            category_source: Reads the category view rows, both levels of the
                tree. Only the roots are summed — a child's budget is already
                part of its root's, so totalling both would double-count it.
            payment_source: Reads the payment rows, over their whole history —
                earlier months are what the trailing series are built from.
            today: The date the current month is taken from. Defaults to today.
            months: How many months each trailing series covers, current
                included.

        """
        self._bank_account_source = bank_account_source
        self._category_source = category_source
        self._payment_source = payment_source
        self._today = today or _today()
        self._months = months

    def _read[ViewT: pydantic.BaseModel](
        self,
        source: "views.ViewSource[ViewT]",
        aggregate: str,
    ) -> "Sequence[ViewT]":
        """Read one aggregate's rows, naming it if the read fails.

        Raises:
            SummaryReadError: The read failed.

        """
        try:
            return source.rows()
        except port_errors.RepositoryError as exc:
            raise errors.SummaryReadError(aggregate) from exc

    def execute(self) -> FinanceSummary:
        """Execute the SummariseFinancesUseCase.

        Returns:
            The figures for this page, unformatted — a caller decides how to
            present them.

        Raises:
            SummaryReadError: One of the reads failed.

        """
        bank_accounts = self._read(self._bank_account_source, "bank accounts")
        categories = self._read(self._category_source, "categories")
        payments = self._read(self._payment_source, "payments")

        keys = _trailing_months(self._today, self._months)
        expenses, nets = _totals_by_month(payments)
        total_balance = sum(account.current_balance for account in bank_accounts)
        roots = [category for category in categories if category.is_root]

        return FinanceSummary(
            total_balance=total_balance,
            balance_history=_balance_history(total_balance, nets, keys),
            total_budget=sum(root.budget for root in roots),
            remaining_budget=sum(root.remaining for root in roots),
            expenditure=expenses.get(_month_key(self._today), 0.0),
            expenditure_history=[expenses.get(key, 0.0) for key in keys],
        )
