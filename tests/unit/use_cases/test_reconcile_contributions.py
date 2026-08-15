"""Tests for the joint-contribution half of ReconcileSubscriptionsUseCase.

A contribution subscription books a linked pair each cadence — the personal
expense every subscription books, plus the joint income that pair settles — so
these tests watch both repositories, not just the personal one.
"""

import datetime
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from domain import entities
from use_cases.reconcile_subscriptions import ReconcileSubscriptionsUseCase

if TYPE_CHECKING:
    from tests import conftest


type PaymentRepo = conftest.FakeRepository[entities.AnyPaymentModel]
UseCaseBuilder = Callable[..., ReconcileSubscriptionsUseCase]

USER_ID = "auth0|test-user-123"
JOINT_ACCOUNT_ID = uuid.uuid4()
BANK_ACCOUNT_ID = uuid.uuid4()
EXPENSE_SOURCE_ID = uuid.uuid4()
JOINT_BANK_ACCOUNT_ID = uuid.uuid4()
JOINT_INCOME_SOURCE_ID = uuid.uuid4()

TODAY = datetime.date(2026, 5, 4)
NEXT_DUE = datetime.date(2026, 6, 1)
AMOUNT = 400.0
SUB_NAME = "Joint standing order"
PAYMENT_NAME = f"Sub: {SUB_NAME}"


@pytest.fixture
def contribution() -> entities.SubscriptionModel:
    """Return a monthly standing order into the joint account."""
    return entities.SubscriptionModel(
        user_id=USER_ID,
        name=SUB_NAME,
        amount=AMOUNT,
        cadence="monthly",
        bank_account_id=BANK_ACCOUNT_ID,
        category_id=EXPENSE_SOURCE_ID,
        start_date=datetime.date(2026, 1, 1),
        joint_bank_account_id=JOINT_BANK_ACCOUNT_ID,
        joint_income_source_id=JOINT_INCOME_SOURCE_ID,
    )


@pytest.fixture
def plain_subscription() -> entities.SubscriptionModel:
    """Return an ordinary subscription, which books only a personal expense."""
    return entities.SubscriptionModel(
        user_id=USER_ID,
        name="Netflix",
        amount=15.99,
        cadence="monthly",
        bank_account_id=BANK_ACCOUNT_ID,
        category_id=EXPENSE_SOURCE_ID,
        start_date=datetime.date(2026, 1, 1),
    )


@pytest.fixture
def personal_repo(build_payment_repo: "conftest.PaymentRepoBuilder") -> "PaymentRepo":
    """Return the payments repository in personal mode."""
    return build_payment_repo(USER_ID)


@pytest.fixture
def joint_repo(build_payment_repo: "conftest.PaymentRepoBuilder") -> "PaymentRepo":
    """Return the payments repository in joint mode, stamping joint ownership."""
    return build_payment_repo(
        USER_ID,
        context={
            "ownership_type": entities.OwnershipType.JOINT.value,
            "joint_account_id": str(JOINT_ACCOUNT_ID),
        },
    )


@pytest.fixture
def build_use_case(
    build_repo: "conftest.RepoBuilder",
    personal_repo: "PaymentRepo",
    joint_repo: "PaymentRepo",
    contribution: entities.SubscriptionModel,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A test overrides only what it varies — the subscriptions on offer, or the
    joint repository a joint-mode instance does not get — and inherits the rest.
    """

    def _build(
        subscriptions: list[entities.SubscriptionModel] | None = None,
        *,
        with_joint_repo: bool = True,
    ) -> ReconcileSubscriptionsUseCase:
        return ReconcileSubscriptionsUseCase(
            subscription_repo=build_repo(
                [contribution] if subscriptions is None else subscriptions,
                parse=entities.SubscriptionModel.model_validate,
            ),
            payment_repo=personal_repo,
            joint_payment_repo=joint_repo if with_joint_repo else None,
            today=TODAY,
        )

    return _build


@pytest.fixture
def use_case(build_use_case: UseCaseBuilder) -> ReconcileSubscriptionsUseCase:
    """Return the use case reconciling one due contribution."""
    return build_use_case()


def _expense_leg(
    sub: entities.SubscriptionModel,
    payment_date: datetime.date,
    *,
    linked_payment_id: uuid.UUID | None = None,
) -> entities.ExpensePaymentModel:
    """Return the personal leg a previous run would have written."""
    return entities.ExpensePaymentModel(
        user_id=USER_ID,
        name=PAYMENT_NAME,
        expense=sub.amount,
        payment_date=payment_date,
        bank_account_id=sub.bank_account_id,
        category_id=sub.category_id,
        subscription_id=sub.id,
        linked_payment_id=linked_payment_id,
    )


def _income_leg(
    sub: entities.SubscriptionModel,
    expense: entities.ExpensePaymentModel,
) -> entities.IncomePaymentModel:
    """Return the joint leg a previous run would have written."""
    return entities.IncomePaymentModel(
        user_id=USER_ID,
        name=PAYMENT_NAME,
        income=sub.amount,
        payment_date=expense.payment_date,
        bank_account_id=JOINT_BANK_ACCOUNT_ID,
        income_source_id=JOINT_INCOME_SOURCE_ID,
        subscription_id=sub.id,
        linked_payment_id=expense.id,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=JOINT_ACCOUNT_ID,
    )


def _expenses(repo: "PaymentRepo") -> list[entities.ExpensePaymentModel]:
    """Return the expense payments the repository was handed, in write order."""
    return [
        payment
        for payment in repo.saved
        if isinstance(payment, entities.ExpensePaymentModel)
    ]


def _incomes(repo: "PaymentRepo") -> list[entities.IncomePaymentModel]:
    """Return the income payments the repository was handed, in write order."""
    return [
        payment
        for payment in repo.saved
        if isinstance(payment, entities.IncomePaymentModel)
    ]


class TestBookingADueContribution:
    """A contribution that is due writes both legs, cross-linked."""

    def test_both_legs_are_written(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        assert all(
            [
                len(_expenses(personal_repo)) > 0,
                len(_incomes(joint_repo)) == 1,
            ],
        )

    def test_the_income_mirrors_the_expense_on_the_joint_side(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        contribution: entities.SubscriptionModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        expense = _expenses(personal_repo)[0]
        income = _incomes(joint_repo)[0]
        assert all(
            [
                income.income == AMOUNT,
                income.payment_date == NEXT_DUE,
                income.bank_account_id == JOINT_BANK_ACCOUNT_ID,
                income.income_source_id == JOINT_INCOME_SOURCE_ID,
                income.subscription_id == contribution.id,
                income.linked_payment_id == expense.id,
                income.name == expense.name,
            ],
        )

    def test_the_income_is_owned_by_the_joint_account(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        income = _incomes(joint_repo)[0]
        assert all(
            [
                income.ownership_type is entities.OwnershipType.JOINT,
                income.joint_account_id == JOINT_ACCOUNT_ID,
            ],
        )

    def test_the_expense_ends_up_pointing_at_the_income(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        # The forward link is a third write: the foreign key means the expense
        # is written unlinked first, so the last copy is the linked one.
        assert _expenses(personal_repo)[-1].linked_payment_id == (
            _incomes(joint_repo)[0].id
        )

    def test_an_ordinary_subscription_books_no_joint_leg(
        self,
        build_use_case: UseCaseBuilder,
        plain_subscription: entities.SubscriptionModel,
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        use_case = build_use_case([plain_subscription])

        # Act
        use_case.execute()

        # Assert
        assert joint_repo.saved == []

    def test_a_joint_instance_leaves_a_contribution_alone(
        self,
        build_use_case: UseCaseBuilder,
        personal_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        # No joint repository, so there is nothing to write the income leg
        # through — booking only the expense would drain the personal side.
        use_case = build_use_case(with_joint_repo=False)

        # Act
        use_case.execute()

        # Assert
        assert personal_repo.saved == []


class TestSupersedingAContribution:
    """A payment a contribution supersedes is removed from both ledgers."""

    @pytest.fixture
    def deactivated(
        self,
        contribution: entities.SubscriptionModel,
    ) -> entities.SubscriptionModel:
        """Return the contribution switched off, so its future pair must go."""
        return entities.SubscriptionModel.model_validate(
            contribution.model_copy(update={"is_active": False}),
        )

    @pytest.fixture
    def booked_pair(
        self,
        contribution: entities.SubscriptionModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel]:
        """Seed a complete future pair, as a previous run would have left it."""
        expense = _expense_leg(contribution, NEXT_DUE)
        income = _income_leg(contribution, expense)
        personal_repo.seed(
            entities.ExpensePaymentModel.model_validate(
                expense.model_copy(update={"linked_payment_id": income.id}),
            ),
        )
        joint_repo.seed(income)
        return expense, income

    def test_the_expense_leg_is_deleted(
        self,
        build_use_case: UseCaseBuilder,
        deactivated: entities.SubscriptionModel,
        booked_pair: tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel],
        personal_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        expense, _ = booked_pair

        # Act
        build_use_case([deactivated]).execute()

        # Assert
        assert personal_repo.deleted == [str(expense.id)]

    def test_the_income_leg_goes_with_it(
        self,
        build_use_case: UseCaseBuilder,
        deactivated: entities.SubscriptionModel,
        booked_pair: tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel],
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        _, income = booked_pair

        # Act
        build_use_case([deactivated]).execute()

        # Assert
        # linked_payment_id is ON DELETE SET NULL, so deleting only the expense
        # would strand this row in the shared books.
        assert joint_repo.deleted == [str(income.id)]


class TestRepairingAHalfWrittenPair:
    """A pair whose expense landed but whose income did not is finished."""

    @pytest.fixture
    def orphaned_expense(
        self,
        contribution: entities.SubscriptionModel,
        personal_repo: "PaymentRepo",
    ) -> entities.ExpensePaymentModel:
        """Seed a future expense with no income leg, as a failed write leaves it."""
        expense = _expense_leg(contribution, NEXT_DUE)
        personal_repo.seed(expense)
        return expense

    def test_the_missing_income_is_written(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        orphaned_expense: entities.ExpensePaymentModel,
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        # Without the repair pass the future expense reads as "already done" and
        # the joint leg is missing forever.
        income = _incomes(joint_repo)[0]
        assert all(
            [
                len(_incomes(joint_repo)) == 1,
                income.linked_payment_id == orphaned_expense.id,
                income.income == AMOUNT,
                income.payment_date == NEXT_DUE,
            ],
        )

    def test_the_repaired_expense_is_linked_forward(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        orphaned_expense: entities.ExpensePaymentModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange / Act
        use_case.execute()

        # Assert
        linked = _expenses(personal_repo)[-1]
        assert all(
            [
                linked.id == orphaned_expense.id,
                linked.linked_payment_id == _incomes(joint_repo)[0].id,
            ],
        )

    def test_an_income_that_already_exists_is_not_written_again(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        contribution: entities.SubscriptionModel,
        orphaned_expense: entities.ExpensePaymentModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        # The income landed; only the third write (the forward link) failed.
        income = _income_leg(contribution, orphaned_expense)
        joint_repo.seed(income)

        # Act
        use_case.execute()

        # Assert
        assert all(
            [
                joint_repo.saved == [],
                _expenses(personal_repo)[-1].linked_payment_id == income.id,
            ],
        )

    def test_a_complete_pair_is_left_alone(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        contribution: entities.SubscriptionModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        expense = _expense_leg(contribution, NEXT_DUE)
        income = _income_leg(contribution, expense)
        personal_repo.seed(
            entities.ExpensePaymentModel.model_validate(
                expense.model_copy(update={"linked_payment_id": income.id}),
            ),
        )
        joint_repo.seed(income)

        # Act
        use_case.execute()

        # Assert
        assert all(
            [
                personal_repo.saved == [],
                joint_repo.saved == [],
                personal_repo.deleted == [],
                joint_repo.deleted == [],
            ],
        )

    def test_a_past_expense_is_never_repaired(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        contribution: entities.SubscriptionModel,
        personal_repo: "PaymentRepo",
        joint_repo: "PaymentRepo",
    ) -> None:
        # Arrange
        # Past payments are never modified, so an old unlinked expense is left
        # as it is — and the subscription is still due for the coming cadence.
        personal_repo.seed(_expense_leg(contribution, datetime.date(2026, 4, 1)))

        # Act
        use_case.execute()

        # Assert
        assert all(
            [
                len(_incomes(joint_repo)) == 1,
                _incomes(joint_repo)[0].payment_date == NEXT_DUE,
            ],
        )
