"""Tests for BankOneOffsUseCase."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

import pytest

from domain import entities
from use_cases.bank_one_offs import BankOneOffsUseCase
from use_cases.errors import AmountToBankLTEZeroError

if TYPE_CHECKING:
    from collections.abc import Callable

USER_ID = "user-123"
BANK_ACCOUNT_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)
ONE_OFFS_ROOT_ID = uuid.uuid4()


@pytest.fixture(name="build_pot")
def _build_pot() -> "Callable[..., entities.CategoryModel]":
    """Return a builder for a one-off pot category."""

    def _build(
        budget: float = 50.0,
        name: str = "Holiday",
        starting_balance: float = 0.0,
    ) -> entities.CategoryModel:
        return entities.CategoryModel(
            user_id=USER_ID,
            name=name,
            parent_id=ONE_OFFS_ROOT_ID,
            accrual=entities.AccrualPeriod.MULTI_MONTH,
            budget=budget,
            starting_balance=starting_balance,
        )

    return _build


@pytest.fixture(name="payment_repo")
def _payment_repo(build_payment_repo: "Callable[..., Any]") -> Any:  # noqa: ANN401
    """Return the payments fake the use case writes through."""
    return build_payment_repo(USER_ID)


@pytest.fixture(name="build_use_case")
def _build_use_case(
    build_repo: "Callable[..., Any]",
    payment_repo: Any,  # noqa: ANN401
) -> "Callable[..., BankOneOffsUseCase]":
    """Return a builder taking the pots the categories repo is seeded with."""

    def _build(pots: list[entities.CategoryModel]) -> BankOneOffsUseCase:
        return BankOneOffsUseCase(
            category_repo=build_repo(pots),
            payment_repo=payment_repo,
        )

    return _build


def test_banking_a_pot_creates_a_payment(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    # Arrange
    pot = build_pot(budget=50.0)
    use_case = build_use_case([pot])

    # Act
    use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    assert len(payment_repo.saved) == 1


def test_payment_is_attributed_to_the_pot_itself(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    """The pot is attributable now, so nothing stands in for it (#250)."""
    # Arrange
    pot = build_pot(budget=50.0)
    use_case = build_use_case([pot])

    # Act
    use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    assert payment_repo.saved[0].category_id == pot.id


def test_payment_fields_reflect_the_banked_pot(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    # Arrange
    pot = build_pot(budget=50.0, name="Holiday")
    use_case = build_use_case([pot])

    # Act
    use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    payment = payment_repo.saved[0]
    expected_expense = 50.0
    assert all(
        [
            payment.expense == expected_expense,
            payment.name == "Bank: Holiday",
            payment.bank_account_id == BANK_ACCOUNT_ID,
            payment.payment_date == PAYMENT_DATE,
            payment.user_id == USER_ID,
        ],
    )


def test_banking_multiple_pots_creates_one_payment_per_pot(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    # Arrange
    pots = [build_pot(budget=50.0, name="Holiday"), build_pot(budget=30.0, name="Car")]
    use_case = build_use_case(pots)

    # Act
    use_case.execute([pot.id for pot in pots], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    expected_saved = 2
    assert len(payment_repo.saved) == expected_saved


def test_banking_a_pot_leaves_the_pot_untouched(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_repo: "Callable[..., Any]",
    payment_repo: Any,  # noqa: ANN401
):
    """Banking writes a payment and nothing else (#250).

    The planned spend is a plan for the month, which nothing decrements, and the
    balance is the opening balance plus attributed payments, so there is no
    stored counter to increment either.
    """
    # Arrange
    pot = build_pot(budget=50.0, starting_balance=100.0)
    category_repo = build_repo([pot])
    use_case = BankOneOffsUseCase(
        category_repo=category_repo,
        payment_repo=payment_repo,
    )

    # Act
    use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    assert category_repo.saved == []


def test_payment_uses_the_planned_spend_not_the_balance(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    """Ensures the payment is the monthly contribution, not what is in the pot."""
    # Arrange
    pot = build_pot(budget=50.0, starting_balance=200.0)
    use_case = build_use_case([pot])

    # Act
    use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    expected_paid = 50.0
    assert payment_repo.saved[0].expense == expected_paid


def test_banking_pot_with_no_planned_spend_raises(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
):
    # Arrange - `budget` is non-negative on the entity, so zero is the only
    # non-positive amount a stored pot can carry.
    pot = build_pot(budget=0.0, name="Holiday")
    use_case = build_use_case([pot])

    # Act
    with pytest.raises(AmountToBankLTEZeroError) as exc_info:
        use_case.execute([pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert - the offending item name is carried as metadata and in the message
    assert all(
        [
            exc_info.value.item_name == "Holiday",
            "Holiday" in str(exc_info.value),
        ],
    )


def test_no_payments_are_written_if_any_pot_has_nothing_to_bank(
    build_pot: "Callable[..., entities.CategoryModel]",
    build_use_case: "Callable[..., BankOneOffsUseCase]",
    payment_repo: Any,  # noqa: ANN401
):
    # Arrange
    good_pot = build_pot(budget=50.0, name="Holiday")
    bad_pot = build_pot(budget=0.0, name="Car")
    use_case = build_use_case([good_pot, bad_pot])

    # Act
    with pytest.raises(AmountToBankLTEZeroError):
        use_case.execute([good_pot.id, bad_pot.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert — every pot is validated before any payment is written, so a single
    # bad one aborts the whole batch with no partial writes.
    assert payment_repo.saved == []
