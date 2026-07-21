"""Tests for ContributeToJointUseCase."""

import datetime
import uuid

import pydantic
import pytest

from domain import entities
from ports import errors as port_errors
from ports import repository
from use_cases import errors
from use_cases.contribute_to_joint import ContributeToJointUseCase

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """In-memory Repository fake for use-case tests.

    Bound to ``pydantic.BaseModel`` rather than ``FinanceTrackerBaseModel``:
    ``JointAccountModel`` carries no user/ownership dimension, so it is not a
    ``FinanceTrackerBaseModel``. The contribution flow only ever reads whole
    tables and writes single rows, so ``get_by_ids`` / ``apply`` are unused.
    """

    def __init__(self, items: list[E] | None = None) -> None:
        """Seed the fake with initial items."""
        self._items: list[E] = list(items or [])
        self.saved: list[E] = []

    def get_all(self) -> list[E]:
        return list(self._items)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        raise NotImplementedError

    def save(self, item: E) -> None:
        self._items.append(item)
        # Snapshot: the expense is saved twice and mutated in between, so
        # storing the live object would make both entries look identical.
        self.saved.append(item.model_copy())

    def apply(self, updates: entities.BackendUpdates) -> None:
        raise NotImplementedError


class FailingRepository[E: pydantic.BaseModel](FakeRepository[E]):
    """Repository fake whose writes always fail at the port boundary."""

    # The item is unused: the stub exists only to fail at the port boundary.
    def save(self, item: E) -> None:  # noqa: ARG002
        msg = "backend unavailable"
        raise port_errors.RepositoryError(msg)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

USER_ID = "user-123"
FROM_BANK_ACCOUNT_ID = uuid.uuid4()
TO_BANK_ACCOUNT_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)
AMOUNT = 250.0


def _make_joint_account(name: str = "Household") -> entities.JointAccountModel:
    return entities.JointAccountModel(name=name)


def _make_joint_expense_source() -> entities.ExpenseSourceModel:
    return entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=entities.BudgetTrackerName.JOINT,
    )


def _make_use_case(
    joint_accounts: list[entities.JointAccountModel] | None = None,
    expense_sources: list[entities.ExpenseSourceModel] | None = None,
    personal_payment_repo: FakeRepository[entities.AnyPaymentModel] | None = None,
    joint_payment_repo: FakeRepository[entities.AnyPaymentModel] | None = None,
) -> tuple[
    ContributeToJointUseCase,
    FakeRepository[entities.AnyPaymentModel],
    FakeRepository[entities.AnyPaymentModel],
]:
    personal_repo = personal_payment_repo or FakeRepository[entities.AnyPaymentModel]()
    joint_repo = joint_payment_repo or FakeRepository[entities.AnyPaymentModel]()
    account_repo: FakeRepository[entities.JointAccountModel] = FakeRepository(
        [_make_joint_account()] if joint_accounts is None else joint_accounts,
    )
    es_repo: FakeRepository[entities.ExpenseSourceModel] = FakeRepository(
        [_make_joint_expense_source()] if expense_sources is None else expense_sources,
    )
    use_case = ContributeToJointUseCase(
        user_id=USER_ID,
        personal_payment_repo=personal_repo,
        joint_payment_repo=joint_repo,
        expense_source_repo=es_repo,
        joint_account_repo=account_repo,
    )
    return use_case, personal_repo, joint_repo


def _saved_expense(
    repo: FakeRepository[entities.AnyPaymentModel],
    index: int = 0,
) -> entities.ExpensePaymentModel:
    """Return a saved payment narrowed to the expense arm of the union."""
    payment = repo.saved[index]
    if not isinstance(payment, entities.ExpensePaymentModel):
        msg = f"expected an expense payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def _saved_income(
    repo: FakeRepository[entities.AnyPaymentModel],
    index: int = 0,
) -> entities.IncomePaymentModel:
    """Return a saved payment narrowed to the income arm of the union."""
    payment = repo.saved[index]
    if not isinstance(payment, entities.IncomePaymentModel):
        msg = f"expected an income payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def _contribute(
    use_case: ContributeToJointUseCase,
    amount: float = AMOUNT,
    payment_date: datetime.date | None = PAYMENT_DATE,
) -> None:
    use_case.execute(
        amount,
        FROM_BANK_ACCOUNT_ID,
        TO_BANK_ACCOUNT_ID,
        payment_date,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_contribution_books_a_personal_expense():
    # Arrange
    expense_source = _make_joint_expense_source()
    use_case, personal_repo, _ = _make_use_case(expense_sources=[expense_source])

    # Act
    _contribute(use_case)

    # Assert
    expense = _saved_expense(personal_repo)
    assert all(
        [
            expense.expense == AMOUNT,
            expense.income == 0,
            expense.expense_source_id == expense_source.id,
            expense.bank_account_id == FROM_BANK_ACCOUNT_ID,
            expense.ownership_type is entities.OwnershipType.PERSONAL,
            expense.payment_date == PAYMENT_DATE,
            expense.user_id == USER_ID,
        ],
    )


def test_contribution_books_a_matching_joint_income():
    # Arrange
    account = _make_joint_account()
    use_case, _, joint_repo = _make_use_case(joint_accounts=[account])

    # Act
    _contribute(use_case)

    # Assert
    income = _saved_income(joint_repo)
    assert all(
        [
            income.income == AMOUNT,
            income.expense == 0,
            income.bank_account_id == TO_BANK_ACCOUNT_ID,
            income.ownership_type is entities.OwnershipType.JOINT,
            income.joint_account_id == account.id,
            income.payment_date == PAYMENT_DATE,
        ],
    )


def test_the_pair_is_cross_linked():
    # Arrange - linked_payment_id is a FK onto payments, so the expense is
    # written unlinked and updated only once the income row exists.
    use_case, personal_repo, joint_repo = _make_use_case()

    # Act
    _contribute(use_case)

    # Assert - the final expense and the income point at each other
    expense = personal_repo.saved[-1]
    income = joint_repo.saved[0]
    assert all(
        [
            income.linked_payment_id == expense.id,
            expense.linked_payment_id == income.id,
        ],
    )


def test_the_expense_is_written_unlinked_before_the_income_exists():
    # Arrange - writing the forward link on the first insert would violate the
    # payments FK, since the income row does not exist yet.
    use_case, personal_repo, _ = _make_use_case()

    # Act
    _contribute(use_case)

    # Assert
    assert personal_repo.saved[0].linked_payment_id is None


def test_contribution_writes_the_expense_twice():
    # Arrange
    use_case, personal_repo, _ = _make_use_case()

    # Act
    _contribute(use_case)

    # Assert - insert, then the back-link update
    expected_writes = 2
    assert len(personal_repo.saved) == expected_writes


def test_both_legs_share_a_name_derived_from_the_account():
    # Arrange
    use_case, personal_repo, joint_repo = _make_use_case(
        joint_accounts=[_make_joint_account(name="Household")],
    )

    # Act
    _contribute(use_case)

    # Assert
    assert all(
        [
            personal_repo.saved[0].name == "Joint: Household",
            joint_repo.saved[0].name == "Joint: Household",
        ],
    )


def test_contribution_defaults_to_today():
    # Arrange
    use_case, personal_repo, _ = _make_use_case()
    today = datetime.datetime.now(tz=datetime.UTC).date()

    # Act
    _contribute(use_case, payment_date=None)

    # Assert
    assert personal_repo.saved[0].payment_date == today


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("amount", [0.0, -0.01, -100.0])
def test_a_non_positive_contribution_is_rejected(amount: float):
    # Arrange
    use_case, _, _ = _make_use_case()

    # Act / Assert
    with pytest.raises(errors.ContributionAmountError) as exc_info:
        _contribute(use_case, amount=amount)

    assert exc_info.value.amount == amount


def test_a_rejected_amount_writes_nothing():
    # Arrange
    use_case, personal_repo, joint_repo = _make_use_case()

    # Act
    with pytest.raises(errors.ContributionAmountError):
        _contribute(use_case, amount=0.0)

    # Assert
    assert all(
        [
            not personal_repo.saved,
            not joint_repo.saved,
        ],
    )


def test_contributing_without_a_joint_account_is_rejected():
    # Arrange
    use_case, _, _ = _make_use_case(joint_accounts=[])

    # Act / Assert
    with pytest.raises(errors.NoJointAccountToContributeToError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_joint_expense_source_is_rejected():
    # Arrange - the hidden "Joint" source is the personal-side anchor, so
    # without it the expense leg has nothing to book against.
    use_case, _, _ = _make_use_case(expense_sources=[])

    # Act / Assert
    with pytest.raises(errors.JointExpenseSourceNotFoundError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_expense_source_writes_nothing():
    # Arrange
    use_case, personal_repo, joint_repo = _make_use_case(expense_sources=[])

    # Act
    with pytest.raises(errors.JointExpenseSourceNotFoundError):
        _contribute(use_case)

    # Assert
    assert all(
        [
            not personal_repo.saved,
            not joint_repo.saved,
        ],
    )


def test_a_failed_write_becomes_a_use_case_error():
    # Arrange
    use_case, _, _ = _make_use_case(
        personal_payment_repo=FailingRepository[entities.AnyPaymentModel](),
    )

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError):
        _contribute(use_case)


def test_a_failed_write_chains_the_repository_error():
    # Arrange
    use_case, _, _ = _make_use_case(
        joint_payment_repo=FailingRepository[entities.AnyPaymentModel](),
    )

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError) as exc_info:
        _contribute(use_case)

    assert isinstance(exc_info.value.__cause__, port_errors.RepositoryError)
