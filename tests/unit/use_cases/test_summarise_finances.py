"""Unit tests for the summarise_finances use case."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest

from domain import entities, read_models
from ports import errors as port_errors
from use_cases import errors, summarise_finances

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import pydantic

_USER_ID = "auth0|test-user-1"
_TODAY = datetime.date(2026, 7, 26)
_CREATED_AT = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)

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
type _CategoryBuilder = Callable[..., read_models.CategoryView]
type _PaymentBuilder = Callable[..., read_models.PaymentView]
type _UseCaseBuilder = Callable[..., summarise_finances.SummariseFinancesUseCase]


class StubViewSource[ViewT: "pydantic.BaseModel"]:
    """``ViewSource`` stub answering one fixed set of rows."""

    def __init__(self, rows: "Sequence[ViewT] | None" = None) -> None:
        """Fix the rows this stub returns."""
        self._rows = list(rows or [])

    def rows(self) -> "list[ViewT]":
        return list(self._rows)


class FailingViewSource[ViewT: "pydantic.BaseModel"]:
    """``ViewSource`` stub whose read always fails at the port boundary."""

    def rows(self) -> "list[ViewT]":
        msg = "the backend is down"
        raise port_errors.RepositoryError(msg)


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
            created_at=_CREATED_AT,
        )

    return _build


@pytest.fixture(name="build_category")
def _build_category() -> "_CategoryBuilder":
    """Return a builder for a category view row, a root unless given a parent."""

    def _build(
        budget: float = 0.0,
        remaining: float = 0.0,
        name: str = entities.BudgetTrackerName.EXPENSES,
        parent_id: uuid.UUID | None = None,
    ) -> read_models.CategoryView:
        return read_models.CategoryView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name=name,
            parent_id=parent_id,
            budget=budget,
            accrued=budget - remaining,
            remaining=remaining,
            progress=0.0,
            split=0.0,
            created_at=_CREATED_AT,
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
            created_at=_CREATED_AT,
        )

    return _build


@pytest.fixture(name="build_use_case")
def _build_use_case() -> "_UseCaseBuilder":
    """Return a builder for the use case, fixed to a known "today".

    A test overrides only the source it varies and inherits empty ones for the
    rest.
    """

    def _build(
        bank_accounts: "Sequence[read_models.BankAccountView] | None" = None,
        categories: "Sequence[read_models.CategoryView] | None" = None,
        payments: "Sequence[read_models.PaymentView] | None" = None,
        today: datetime.date = _TODAY,
        months: int = 3,
    ) -> summarise_finances.SummariseFinancesUseCase:
        return summarise_finances.SummariseFinancesUseCase(
            bank_account_source=StubViewSource[read_models.BankAccountView](
                bank_accounts,
            ),
            category_source=StubViewSource[read_models.CategoryView](
                categories,
            ),
            payment_source=StubViewSource[read_models.PaymentView](payments),
            today=today,
            months=months,
        )

    return _build


def test_total_balance_sums_every_account(
    build_use_case: "_UseCaseBuilder",
    build_bank_account: "_BankAccountBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        bank_accounts=[
            build_bank_account(_CURRENT_ACCOUNT),
            build_bank_account(_SAVINGS_ACCOUNT),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.total_balance == _CURRENT_ACCOUNT + _SAVINGS_ACCOUNT


def test_budget_totals_sum_every_root(
    build_use_case: "_UseCaseBuilder",
    build_category: "_CategoryBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        categories=[
            build_category(
                budget=_EXPENSES_BUDGET,
                remaining=_EXPENSES_REMAINING,
            ),
            build_category(
                budget=_SAVINGS_BUDGET,
                remaining=_SAVINGS_REMAINING,
                name=entities.BudgetTrackerName.SAVINGS,
            ),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert all(
        [
            figures.total_budget == _EXPENSES_BUDGET + _SAVINGS_BUDGET,
            figures.remaining_budget == _EXPENSES_REMAINING + _SAVINGS_REMAINING,
        ],
    )


def test_budget_totals_ignore_children(
    build_use_case: "_UseCaseBuilder",
    build_category: "_CategoryBuilder",
) -> None:
    # Arrange - a child's budget is already part of its root's, so totalling
    # both levels would count it twice.
    root = build_category(budget=_EXPENSES_BUDGET, remaining=_EXPENSES_REMAINING)
    use_case = build_use_case(
        categories=[
            root,
            build_category(
                budget=_SAVINGS_BUDGET,
                remaining=_SAVINGS_REMAINING,
                name="Groceries",
                parent_id=root.id,
            ),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert all(
        [
            figures.total_budget == _EXPENSES_BUDGET,
            figures.remaining_budget == _EXPENSES_REMAINING,
        ],
    )


def test_expenditure_counts_only_the_current_month(
    build_use_case: "_UseCaseBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        payments=[
            build_payment(datetime.date(2026, 7, 1), expense=_EARLY_EXPENSE),
            build_payment(datetime.date(2026, 7, 26), expense=_LATE_EXPENSE),
            build_payment(datetime.date(2026, 6, 30), expense=999.0),
            build_payment(datetime.date(2026, 7, 5), income=500.0),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.expenditure == _EARLY_EXPENSE + _LATE_EXPENSE


def test_expenditure_history_runs_oldest_to_newest(
    build_use_case: "_UseCaseBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange - May is left empty so a month with no payments still gets a slot.
    use_case = build_use_case(
        payments=[
            build_payment(datetime.date(2026, 6, 15), expense=60.0),
            build_payment(datetime.date(2026, 7, 15), expense=70.0),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.expenditure_history == [0.0, 60.0, 70.0]


def test_history_rolls_back_across_the_year_boundary(
    build_use_case: "_UseCaseBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        payments=[build_payment(datetime.date(2025, 12, 3), expense=25.0)],
        today=datetime.date(2026, 1, 15),
    )

    # Act
    figures = use_case.execute()

    # Assert - December of the preceding year sits directly before January.
    assert figures.expenditure_history == [0.0, 25.0, 0.0]


def test_balance_history_undoes_each_months_net_movement(
    build_use_case: "_UseCaseBuilder",
    build_bank_account: "_BankAccountBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange - only the current balance is stored, so June's close is today's
    # balance less July's net (+100 income, -30 expense = +70), and May's is
    # June's less June's net (-50), which puts it back up at 480.
    use_case = build_use_case(
        bank_accounts=[build_bank_account(500.0)],
        payments=[
            build_payment(datetime.date(2026, 7, 10), income=100.0),
            build_payment(datetime.date(2026, 7, 20), expense=30.0),
            build_payment(datetime.date(2026, 6, 10), expense=50.0),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.balance_history == [480.0, 430.0, 500.0]


def test_expenditure_delta_compares_against_last_month(
    build_use_case: "_UseCaseBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        payments=[
            build_payment(datetime.date(2026, 6, 15), expense=_JUNE_SPEND),
            build_payment(datetime.date(2026, 7, 15), expense=_JULY_SPEND),
        ],
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.expenditure_delta == _JULY_SPEND - _JUNE_SPEND


def test_expenditure_delta_is_unknown_without_a_prior_month(
    build_use_case: "_UseCaseBuilder",
    build_payment: "_PaymentBuilder",
) -> None:
    # Arrange
    use_case = build_use_case(
        payments=[build_payment(datetime.date(2026, 7, 15), expense=30.0)],
        months=1,
    )

    # Act
    figures = use_case.execute()

    # Assert
    assert figures.expenditure_delta is None


def test_summarising_nothing_reports_zeroes(
    build_use_case: "_UseCaseBuilder",
) -> None:
    # Arrange - a brand-new workspace has no accounts, categories, or payments.
    use_case = build_use_case()

    # Act
    figures = use_case.execute()

    # Assert
    assert all(
        [
            figures.total_balance == 0.0,
            figures.remaining_budget == 0.0,
            figures.expenditure == 0.0,
            figures.balance_history == [0.0, 0.0, 0.0],
        ],
    )


def test_a_failed_read_is_reported_as_a_use_case_error() -> None:
    # Arrange - a RepositoryError must not escape the use case untranslated,
    # and the error should name which read failed.
    use_case = summarise_finances.SummariseFinancesUseCase(
        bank_account_source=StubViewSource[read_models.BankAccountView](),
        category_source=FailingViewSource[read_models.CategoryView](),
        payment_source=StubViewSource[read_models.PaymentView](),
    )

    # Act
    with pytest.raises(errors.SummaryReadError) as raised:
        use_case.execute()

    # Assert
    assert raised.value.aggregate == "categories"
