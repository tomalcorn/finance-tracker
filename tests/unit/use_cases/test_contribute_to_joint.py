"""Tests for ContributeToJointUseCase."""

import datetime
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from tests import conftest


USER_ID = "user-123"
FROM_BANK_ACCOUNT_ID = uuid.uuid4()
TO_BANK_ACCOUNT_ID = uuid.uuid4()
INCOME_SOURCE_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)
AMOUNT = 250.0
ACCOUNT_NAME = "Household"


type PaymentRepo = conftest.FakeRepository[entities.AnyPaymentModel]
UseCaseBuilder = Callable[..., ContributeToJointUseCase]


@pytest.fixture
def personal_repo(build_payment_repo: Callable[..., PaymentRepo]) -> PaymentRepo:
    """Return the payments repository in personal mode."""
    return build_payment_repo(USER_ID)


@pytest.fixture
def joint_repo(build_payment_repo: Callable[..., PaymentRepo]) -> PaymentRepo:
    """Return the payments repository in joint mode."""
    return build_payment_repo(USER_ID)


@pytest.fixture
def failing_repo(build_payment_repo: Callable[..., PaymentRepo]) -> PaymentRepo:
    """Return a payments repository whose writes fail at the port boundary."""
    repo = build_payment_repo(USER_ID)
    repo.save_error = port_errors.RepositoryError("backend unavailable")
    return repo


@pytest.fixture
def joint_account() -> entities.JointAccountModel:
    """Return the joint account the contribution targets."""
    return entities.JointAccountModel(name=ACCOUNT_NAME)


@pytest.fixture
def joint_root_category() -> entities.CategoryModel:
    """Return the "Joint" root category the personal leg books against."""
    return entities.CategoryModel(
        user_id=USER_ID,
        name=entities.BudgetTrackerName.JOINT,
    )


@pytest.fixture
def build_use_case(
    build_repo: "conftest.RepoBuilder",
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
    joint_account: entities.JointAccountModel,
    joint_root_category: entities.CategoryModel,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A failure test overrides exactly the collaborator it wants to vary (an
    empty account or source list, or a repository that fails on write) and
    inherits the rest.
    """

    def _build(
        *,
        accounts: list[entities.JointAccountModel] | None = None,
        categories: list[entities.CategoryModel] | None = None,
        personal: PaymentRepo | None = None,
        joint: PaymentRepo | None = None,
    ) -> ContributeToJointUseCase:
        return ContributeToJointUseCase(
            user_id=USER_ID,
            personal_payment_repo=personal or personal_repo,
            joint_payment_repo=joint or joint_repo,
            category_repo=build_repo(
                [joint_root_category] if categories is None else categories,
            ),
            joint_account_repo=build_repo(
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
    use_case.execute(
        amount,
        FROM_BANK_ACCOUNT_ID,
        TO_BANK_ACCOUNT_ID,
        INCOME_SOURCE_ID,
        PAYMENT_DATE,
    )


def test_contribution_books_a_personal_expense(
    use_case: ContributeToJointUseCase,
    personal_repo: PaymentRepo,
    joint_root_category: entities.CategoryModel,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert
    expense = _saved_expense(personal_repo)
    assert all(
        [
            expense.expense == AMOUNT,
            expense.income == 0,
            expense.category_id == joint_root_category.id,
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


def test_the_joint_income_is_booked_against_the_chosen_income_source(
    use_case: ContributeToJointUseCase,
    joint_repo: PaymentRepo,
):
    # Arrange / Act
    _contribute(use_case)

    # Assert - an unsourced income would be missing from the joint roll-ups.
    assert _saved_income(joint_repo).income_source_id == INCOME_SOURCE_ID


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


def test_a_child_category_named_joint_is_not_the_anchor(
    build_use_case: UseCaseBuilder,
):
    # Arrange - the anchor is the *root* called "Joint"; a user's own
    # subcategory of that name is an ordinary category and must not stand in
    # for it.
    use_case = build_use_case(
        categories=[
            entities.CategoryModel(
                user_id=USER_ID,
                name=entities.BudgetTrackerName.JOINT,
                parent_id=uuid.uuid4(),
            ),
        ],
    )

    # Act / Assert
    with pytest.raises(errors.JointCategoryNotFoundError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_joint_category_is_rejected(
    build_use_case: UseCaseBuilder,
):
    # Arrange - the "Joint" root is the personal-side anchor, so without it the
    # expense leg has nothing to book against.
    use_case = build_use_case(categories=[])

    # Act / Assert
    with pytest.raises(errors.JointCategoryNotFoundError) as exc_info:
        _contribute(use_case)

    assert exc_info.value.user_id == USER_ID


def test_a_missing_joint_category_writes_nothing(
    build_use_case: UseCaseBuilder,
    personal_repo: PaymentRepo,
    joint_repo: PaymentRepo,
):
    # Arrange
    use_case = build_use_case(categories=[])

    # Act
    with pytest.raises(errors.JointCategoryNotFoundError):
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
    failing_repo: PaymentRepo,
):
    # Arrange
    use_case = build_use_case(personal=failing_repo)

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError):
        _contribute(use_case)


def test_a_failed_write_chains_the_repository_error(
    build_use_case: UseCaseBuilder,
    failing_repo: PaymentRepo,
):
    # Arrange
    use_case = build_use_case(joint=failing_repo)

    # Act / Assert
    with pytest.raises(errors.ContributionWriteError) as exc_info:
        _contribute(use_case)

    assert isinstance(exc_info.value.__cause__, port_errors.RepositoryError)
