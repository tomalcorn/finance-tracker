"""Tests for LogQuickPaymentUseCase."""

import datetime
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors
from use_cases.log_quick_payment import LogQuickPaymentUseCase

if TYPE_CHECKING:
    from tests import conftest

USER_ID = "user-123"
BANK_ACCOUNT_ID = uuid.uuid4()
EXPENSE_SOURCE_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)
COFFEE_PRICE = 3.5

type PaymentRepo = conftest.FakeRepository[entities.AnyPaymentModel]
type QuickButtonRepo = conftest.FakeRepository[entities.QuickButtonModel]
UseCaseBuilder = Callable[..., LogQuickPaymentUseCase]


@pytest.fixture
def quick_button() -> entities.QuickButtonModel:
    """Return the button that is tapped."""
    return entities.QuickButtonModel(
        user_id=USER_ID,
        name="Coffee",
        expense=COFFEE_PRICE,
        bank_account_id=BANK_ACCOUNT_ID,
        expense_source_id=EXPENSE_SOURCE_ID,
        icon="☕",
    )


@pytest.fixture
def payment_repo(build_payment_repo: Callable[..., PaymentRepo]) -> PaymentRepo:
    """Return the payments repository the tap writes through."""
    return build_payment_repo(USER_ID)


@pytest.fixture
def build_use_case(
    build_repo: "conftest.RepoBuilder",
    quick_button: entities.QuickButtonModel,
    payment_repo: PaymentRepo,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A failure test overrides exactly the collaborator it varies (an empty or
    failing button repository, a failing payments repository) and inherits the
    rest.
    """

    def _build(
        *,
        buttons: "QuickButtonRepo | None" = None,
        payments: PaymentRepo | None = None,
    ) -> LogQuickPaymentUseCase:
        return LogQuickPaymentUseCase(
            quick_button_repo=buttons or build_repo([quick_button]),
            payment_repo=payments or payment_repo,
        )

    return _build


@pytest.fixture
def use_case(build_use_case: UseCaseBuilder) -> LogQuickPaymentUseCase:
    """Return the use case wired to the standard happy-path collaborators."""
    return build_use_case()


def _saved_expense(repo: PaymentRepo) -> entities.ExpensePaymentModel:
    """Return the last saved payment, narrowed to the expense arm of the union."""
    payment = repo.saved[-1]
    if not isinstance(payment, entities.ExpensePaymentModel):
        msg = f"expected an expense payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def test_execute_writes_the_preset_the_button_holds(
    use_case: LogQuickPaymentUseCase,
    quick_button: entities.QuickButtonModel,
    payment_repo: PaymentRepo,
) -> None:
    # Arrange - the button and repositories come from the fixtures.

    # Act
    use_case.execute(quick_button.id, payment_date=PAYMENT_DATE)

    # Assert - the payment carries the button's name, amount, and references
    payment = _saved_expense(payment_repo)
    assert all(
        [
            payment.name == "Coffee",
            payment.expense == COFFEE_PRICE,
            payment.bank_account_id == BANK_ACCOUNT_ID,
            payment.expense_source_id == EXPENSE_SOURCE_ID,
            payment.payment_date == PAYMENT_DATE,
            payment.payment_type == "expense",
            payment.checked is False,
        ],
    )


def test_execute_dates_the_payment_today_by_default(
    use_case: LogQuickPaymentUseCase,
    quick_button: entities.QuickButtonModel,
    payment_repo: PaymentRepo,
) -> None:
    # Arrange
    today = datetime.datetime.now(tz=datetime.UTC).date()

    # Act
    use_case.execute(quick_button.id)

    # Assert
    assert _saved_expense(payment_repo).payment_date == today


def test_execute_writes_the_payment_through_the_gate(
    use_case: LogQuickPaymentUseCase,
    quick_button: entities.QuickButtonModel,
    payment_repo: PaymentRepo,
) -> None:
    # Arrange - the use case never sets the owner itself, so an owned payment is
    # proof the raw row was completed by the repository's gate.

    # Act
    use_case.execute(quick_button.id)

    # Assert
    assert _saved_expense(payment_repo).user_id == USER_ID


def test_execute_returns_the_payment_it_wrote(
    use_case: LogQuickPaymentUseCase,
    quick_button: entities.QuickButtonModel,
    payment_repo: PaymentRepo,
) -> None:
    # Arrange - the collaborators come from the fixtures.

    # Act
    payment = use_case.execute(quick_button.id)

    # Assert
    assert payment == _saved_expense(payment_repo)


def test_execute_leaves_an_uncategorised_button_uncategorised(
    build_use_case: UseCaseBuilder,
    build_repo: "conftest.RepoBuilder",
    payment_repo: PaymentRepo,
) -> None:
    # Arrange - a button with no expense source still logs a valid payment
    button = entities.QuickButtonModel(
        user_id=USER_ID,
        name="Parking",
        expense=2.0,
        bank_account_id=BANK_ACCOUNT_ID,
    )
    use_case = build_use_case(buttons=build_repo([button]))

    # Act
    use_case.execute(button.id)

    # Assert
    assert _saved_expense(payment_repo).expense_source_id is None


def test_execute_raises_when_the_button_no_longer_exists(
    build_use_case: UseCaseBuilder,
    build_repo: "conftest.RepoBuilder",
) -> None:
    # Arrange - the button was removed since the page rendered
    button_id = uuid.uuid4()
    use_case = build_use_case(buttons=build_repo([]))

    # Act / Assert
    with pytest.raises(errors.QuickButtonNotFoundError) as exc_info:
        use_case.execute(button_id)

    assert exc_info.value.button_id == str(button_id)


def test_execute_writes_nothing_when_the_button_no_longer_exists(
    build_use_case: UseCaseBuilder,
    build_repo: "conftest.RepoBuilder",
    payment_repo: PaymentRepo,
) -> None:
    # Arrange
    use_case = build_use_case(buttons=build_repo([]))

    # Act
    with pytest.raises(errors.QuickButtonNotFoundError):
        use_case.execute(uuid.uuid4())

    # Assert
    assert payment_repo.saved == []


def test_execute_wraps_a_failed_button_read(
    build_use_case: UseCaseBuilder,
    build_repo: "conftest.RepoBuilder",
    quick_button: entities.QuickButtonModel,
) -> None:
    # Arrange
    buttons = build_repo([quick_button])
    buttons.read_error = port_errors.RepositoryError("backend unavailable")
    use_case = build_use_case(buttons=buttons)

    # Act / Assert
    with pytest.raises(errors.QuickPaymentWriteError):
        use_case.execute(quick_button.id)


def test_execute_wraps_a_failed_payment_write(
    build_use_case: UseCaseBuilder,
    build_payment_repo: Callable[..., PaymentRepo],
    quick_button: entities.QuickButtonModel,
) -> None:
    # Arrange
    payments = build_payment_repo(USER_ID)
    payments.save_error = port_errors.RepositoryError("backend unavailable")
    use_case = build_use_case(payments=payments)

    # Act / Assert
    with pytest.raises(errors.QuickPaymentWriteError):
        use_case.execute(quick_button.id)
