"""Tests for ContributeToJointUseCase."""

import datetime
import uuid
from collections.abc import Callable

import pydantic
import pytest

from domain import entities
from ports import errors as port_errors
from ports import repository
from use_cases import errors
from use_cases.contribute_to_joint import ContributeToJointUseCase

USER_ID = "user-123"
FROM_BANK_ACCOUNT_ID = uuid.uuid4()
TO_BANK_ACCOUNT_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)
AMOUNT = 250.0
ACCOUNT_NAME = "Household"


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


PaymentRepo = FakeRepository[entities.AnyPaymentModel]
UseCaseBuilder = Callable[..., ContributeToJointUseCase]


@pytest.fixture
def personal_repo() -> PaymentRepo:
    """Return the payments repository in personal mode."""
    return PaymentRepo()


@pytest.fixture
def joint_repo() -> PaymentRepo:
    """Return the payments repository in joint mode."""
    return PaymentRepo()


@pytest.fixture
def joint_account() -> entities.JointAccountModel:
    """Return the joint account the contribution targets."""
    return entities.JointAccountModel(name=ACCOUNT_NAME)


@pytest.fixture
def joint_expense_source() -> entities.ExpenseSourceModel:
    """Return the hidden "Joint" expense source the personal leg books against."""
    return entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=entities.BudgetTrackerName.JOINT,
    )


@pytest.fixture
def build_use_case(
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
    joint_account: entities.JointAccountModel,
    joint_expense_source: entities.ExpenseSourceModel,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A failure test overrides exactly the collaborator it wants to vary (an
    empty account or source list, or a repository that fails on write) and
    inherits the rest.
    """

    def _build(
        *,
        accounts: list[entities.JointAccountModel] | None = None,
        expense_sources: list[entities.ExpenseSourceModel] | None = None,
        personal: PaymentRepo | None = None,
        joint: PaymentRepo | None = None,
    ) -> ContributeToJointUseCase:
        return ContributeToJointUseCase(
            user_id=USER_ID,
            personal_payment_repo=personal or personal_repo,
            joint_payment_repo=joint or joint_repo,
            expense_source_repo=FakeRepository(
                [joint_expense_source] if expense_sources is None else expense_sources,
            ),
            joint_account_repo=FakeRepository(
                [joint_account] if accounts is None else accounts,
            ),
        )

    return _build


@pytest.fixture
def use_case(build_use_case: UseCaseBuilder) -> ContributeToJointUseCase:
    """Return the use case wired to the standard happy-path collaborators."""
    return build_use_case()


def _saved_expense(repo: PaymentRepo, index: int = -1) -> entities.ExpensePaymentModel:
    """Return a saved payment narrowed to the expense arm of the union."""
    payment = repo.saved[index]
    if not isinstance(payment, entities.ExpensePaymentModel):
        msg = f"expected an expense payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def _saved_income(repo: PaymentRepo, index: int = -1) -> entities.IncomePaymentModel:
    """Return a saved payment narrowed to the income arm of the union."""
    payment = repo.saved[index]
    if not isinstance(payment, entities.IncomePaymentModel):
        msg = f"expected an income payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def _contribute(
    use_case: ContributeToJointUseCase,
    amount: float = AMOUNT,
) -> None:
    use_case.execute(amount, FROM_BANK_ACCOUNT_ID, TO_BANK_ACCOUNT_ID, PAYMENT_DATE)


def test_contribution_books_a_personal_expense(
    use_case: ContributeToJointUseCase,
    personal_repo: PaymentRepo,
    joint_expense_source: entities.ExpenseSourceModel,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert
    expense = _saved_expense(personal_repo)
    assert all(
        [
            expense.expense == AMOUNT,
            expense.income == 0,
            expense.expense_source_id == joint_expense_source.id,
            expense.bank_account_id == FROM_BANK_ACCOUNT_ID,
            expense.ownership_type is entities.OwnershipType.PERSONAL,
            expense.payment_date == PAYMENT_DATE,
            expense.user_id == USER_ID,
        ],
    )


def test_contribution_books_a_matching_joint_income(
    use_case: ContributeToJointUseCase,
    joint_repo: PaymentRepo,
    joint_account: entities.JointAccountModel,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert
    income = _saved_income(joint_repo)
    assert all(
        [
            income.income == AMOUNT,
            income.expense == 0,
            income.bank_account_id == TO_BANK_ACCOUNT_ID,
            income.ownership_type is entities.OwnershipType.JOINT,
            income.joint_account_id == joint_account.id,
            income.payment_date == PAYMENT_DATE,
        ],
    )


def test_the_pair_is_traceable_to_each_other(
    use_case: ContributeToJointUseCase,
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert - each leg carries the other's id, so the transfer is traceable
    # from either dashboard.
    expense = _saved_expense(personal_repo)
    income = _saved_income(joint_repo)
    assert all(
        [
            income.linked_payment_id == expense.id,
            expense.linked_payment_id == income.id,
        ],
    )


def test_both_legs_share_a_name_derived_from_the_account(
    use_case: ContributeToJointUseCase,
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert
    assert all(
        [
            _saved_expense(personal_repo).name == f"Joint: {ACCOUNT_NAME}",
            _saved_income(joint_repo).name == f"Joint: {ACCOUNT_NAME}",
        ],
    )


@pytest.mark.parametrize("amount", [0.0, -0.01, -100.0])
def test_a_non_positive_contribution_is_rejected(
    use_case: ContributeToJointUseCase,
    amount: float,
):
    # Arrange / Act / Assert
    with pytest.raises(errors.ContributionAmountError) as exc_info:
        _contribute(use_case, amount=amount)

    assert exc_info.value.amount == amount


def test_a_rejected_amount_writes_nothing(
    use_case: ContributeToJointUseCase,
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
):
    # Arrange / Act
    with pytest.raises(errors.ContributionAmountError):
        _contribute(use_case, amount=0.0)

    # Assert
    assert all(
        [
            not personal_repo.saved,
            not joint_repo.saved,
        ],
    )


def test_contributing_without_a_joint_account_is_rejected(
    build_use_case: UseCaseBuilder,
):
    # Arrange
    use_case = build_use_case(accounts=[])

    # Act / Assert
    with pytest.raises(errors.NoJointAccountToContributeToError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_joint_expense_source_is_rejected(
    build_use_case: UseCaseBuilder,
):
    # Arrange - the hidden "Joint" source is the personal-side anchor, so
    # without it the expense leg has nothing to book against.
    use_case = build_use_case(expense_sources=[])

    # Act / Assert
    with pytest.raises(errors.JointExpenseSourceNotFoundError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_expense_source_writes_nothing(
    build_use_case: UseCaseBuilder,
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
):
    # Arrange
    use_case = build_use_case(expense_sources=[])

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


def test_a_failed_write_becomes_a_use_case_error(
    build_use_case: UseCaseBuilder,
):
    # Arrange
    use_case = build_use_case(personal=FailingRepository[entities.AnyPaymentModel]())

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError):
        _contribute(use_case)


def test_a_failed_write_chains_the_repository_error(
    build_use_case: UseCaseBuilder,
):
    # Arrange
    use_case = build_use_case(joint=FailingRepository[entities.AnyPaymentModel]())

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError) as exc_info:
        _contribute(use_case)

    assert isinstance(exc_info.value.__cause__, port_errors.RepositoryError)
