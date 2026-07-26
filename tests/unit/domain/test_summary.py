"""Unit tests for the dashboard summary calculation."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest

from domain import entities, read_models, summary

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_USER_ID = "auth0|test-user-1"
_TODAY = datetime.date(2026, 7, 26)

# Named so each assertion can state the arithmetic it expects rather than a
# magic total.
_CURRENT_ACCOUNT = 120.50
_SAVINGS_ACCOUNT = 79.50
_EXPENSES_BUDGET = 800.0
_EXPENSES_REMAINING = 300.0
_SAVINGS_BUDGET = 200.0
_SAVINGS_REMAINING = 50.0
_EARLY_EXPENSE = 40.0
_LATE_EXPENSE = 10.0
_JUNE_SPEND = 80.0
_JULY_SPEND = 30.0

type _BankAccountBuilder = Callable[..., read_models.BankAccountView]
type _BudgetTrackerBuilder = Callable[..., read_models.BudgetTrackerView]
type _PaymentBuilder = Callable[..., read_models.PaymentView]
type _Summariser = Callable[..., summary.DashboardSummary]


@pytest.fixture(name="build_bank_account")
def _build_bank_account() -> "_BankAccountBuilder":
    """Return a builder for a bank account view row."""

    def _build(current_balance: float = 0.0) -> read_models.BankAccountView:
        return read_models.BankAccountView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name="Current Account",
            starting_balance=0.0,
            current_balance=current_balance,
        )

    return _build


@pytest.fixture(name="build_budget_tracker")
def _build_budget_tracker() -> "_BudgetTrackerBuilder":
    """Return a builder for a budget tracker view row."""

    def _build(
        total_budget: float = 0.0,
        remaining: float = 0.0,
        name: entities.BudgetTrackerName = entities.BudgetTrackerName.EXPENSES,
    ) -> read_models.BudgetTrackerView:
        return read_models.BudgetTrackerView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name=name,
            total_budget=total_budget,
            current_month=total_budget - remaining,
            remaining=remaining,
            progress=0.0,
            split=0.0,
        )

    return _build


@pytest.fixture(name="build_payment")
def _build_payment() -> "_PaymentBuilder":
    """Return a builder for a payment row."""

    def _build(
        payment_date: datetime.date = _TODAY,
        expense: float = 0.0,
        income: float = 0.0,
    ) -> read_models.PaymentView:
        return read_models.PaymentView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name="Payment",
            payment_date=payment_date,
            payment_type="income" if income else "expense",
            expense=expense,
            income=income,
            checked=False,
            bank_account_id=uuid.uuid4(),
        )

    return _build


@pytest.fixture(name="summarise")
def _summarise() -> "_Summariser":
    """Return a summariser fixed to a known "today", varying only its rows."""

    def _summarise(
        bank_accounts: "Sequence[read_models.BankAccountView] | None" = None,
        budget_trackers: "Sequence[read_models.BudgetTrackerView] | None" = None,
        payments: "Sequence[read_models.PaymentView] | None" = None,
        today: datetime.date = _TODAY,
        months: int = 3,
    ) -> summary.DashboardSummary:
        return summary.summarise(
            bank_accounts or [],
            budget_trackers or [],
            payments or [],
            today,
            months,
        )

    return _summarise


def test_total_balance_sums_every_account(
    summarise: "_Summariser",
    build_bank_account: "_BankAccountBuilder",
) -> None:
    # Arrange
    accounts = [
        build_bank_account(_CURRENT_ACCOUNT),
        build_bank_account(_SAVINGS_ACCOUNT),
    ]

    # Act
    figures = summarise(bank_accounts=accounts)

    # Assert
    assert figures.total_balance == _CURRENT_ACCOUNT + _SAVINGS_ACCOUNT


def test_budget_totals_sum_every_tracker(
    summarise: "_Summariser",
    build_budget_tracker: "_BudgetTrackerBuilder",
) -> None:
    # Arrange
    trackers = [
        build_budget_tracker(
            total_budget=_EXPENSES_BUDGET,
            remaining=_EXPENSES_REMAINING,
        ),
        build_budget_tracker(
            total_budget=_SAVINGS_BUDGET,
            remaining=_SAVINGS_REMAINING,
            name=entities.BudgetTrackerName.SAVINGS,
        ),
    ]

    # Act
    figures = summarise(budget_trackers=trackers)

    # Assert
    assert all(
        [
            figures.total_budget == _EXPENSES_BUDGET + _SAVINGS_BUDGET,
            figures.remaining_budget == _EXPENSES_REMAINING + _SAVINGS_REMAINING,
        ],
    )


def test_expenditure_counts_only_the_current_month(
    summarise: "_Summariser",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    payments = [
        build_payment(datetime.date(2026, 7, 1), expense=_EARLY_EXPENSE),
        build_payment(datetime.date(2026, 7, 26), expense=_LATE_EXPENSE),
        build_payment(datetime.date(2026, 6, 30), expense=999.0),
        build_payment(datetime.date(2026, 7, 5), income=500.0),
    ]

    # Act
    figures = summarise(payments=payments)

    # Assert
    assert figures.expenditure == _EARLY_EXPENSE + _LATE_EXPENSE


def test_expenditure_history_runs_oldest_to_newest(
    summarise: "_Summariser",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange - May is left empty so a month with no payments still gets a slot.
    payments = [
        build_payment(datetime.date(2026, 6, 15), expense=60.0),
        build_payment(datetime.date(2026, 7, 15), expense=70.0),
    ]

    # Act
    figures = summarise(payments=payments)

    # Assert
    assert figures.expenditure_history == (0.0, 60.0, 70.0)


def test_history_rolls_back_across_the_year_boundary(
    summarise: "_Summariser",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    payments = [build_payment(datetime.date(2025, 12, 3), expense=25.0)]

    # Act
    figures = summarise(payments=payments, today=datetime.date(2026, 1, 15))

    # Assert - December of the preceding year sits directly before January.
    assert figures.expenditure_history == (0.0, 25.0, 0.0)


def test_balance_history_undoes_each_months_net_movement(
    summarise: "_Summariser",
    build_bank_account: "_BankAccountBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange - only the current balance is stored, so June's close is today's
    # balance less July's net (+100 income, -30 expense = +70), and May's is
    # June's less June's net (-50), which puts it back up at 480.
    accounts = [build_bank_account(500.0)]
    payments = [
        build_payment(datetime.date(2026, 7, 10), income=100.0),
        build_payment(datetime.date(2026, 7, 20), expense=30.0),
        build_payment(datetime.date(2026, 6, 10), expense=50.0),
    ]

    # Act
    figures = summarise(bank_accounts=accounts, payments=payments)

    # Assert
    assert figures.balance_history == (480.0, 430.0, 500.0)


def test_expenditure_delta_compares_against_last_month(
    summarise: "_Summariser",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    payments = [
        build_payment(datetime.date(2026, 6, 15), expense=_JUNE_SPEND),
        build_payment(datetime.date(2026, 7, 15), expense=_JULY_SPEND),
    ]

    # Act
    figures = summarise(payments=payments)

    # Assert
    assert figures.expenditure_delta == _JULY_SPEND - _JUNE_SPEND


def test_expenditure_delta_is_unknown_without_a_prior_month(
    summarise: "_Summariser",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    payments = [build_payment(datetime.date(2026, 7, 15), expense=30.0)]

    # Act
    figures = summarise(payments=payments, months=1)

    # Assert
    assert figures.expenditure_delta is None


def test_summarising_nothing_reports_zeroes(summarise: "_Summariser") -> None:
    # Arrange - a brand-new workspace has no accounts, trackers, or payments.

    # Act
    figures = summarise()

    # Assert
    assert all(
        [
            figures.total_balance == 0.0,
            figures.remaining_budget == 0.0,
            figures.expenditure == 0.0,
            figures.balance_history == (0.0, 0.0, 0.0),
        ],
    )
