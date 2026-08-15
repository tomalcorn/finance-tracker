"""Unit tests for ReconcileSubscriptionsUseCase."""

import datetime
import typing
import uuid
from collections.abc import Callable
from unittest import mock

import pytest

from domain import entities
from domain.errors import InvalidSubscriptionCadenceError
from use_cases.errors import InvalidCadenceError
from use_cases.reconcile_subscriptions import ReconcileSubscriptionsUseCase

type Cadence = typing.Literal[
    "weekly",
    "monthly",
    "quarterly",
    "biannually",
    "yearly",
]

type SubscriptionBuilder = Callable[..., entities.SubscriptionModel]
type PaymentBuilder = Callable[..., entities.ExpensePaymentModel]
type UseCaseBuilder = Callable[..., ReconcileSubscriptionsUseCase]

_TODAY = datetime.date(2026, 5, 4)
_FUTURE = _TODAY + datetime.timedelta(days=30)
_DEFAULT_AMOUNT = 15.99
_DEFAULT_NAME = "Netflix"


@pytest.fixture(name="user_id")
def _user_id() -> str:
    return "auth0|test-user-123"


@pytest.fixture(name="bank_account_id")
def _bank_account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(name="category_id")
def _category_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(name="mock_subscription_repo")
def _mock_subscription_repo() -> mock.MagicMock:
    return mock.MagicMock()


@pytest.fixture(name="mock_payment_repo")
def _mock_payment_repo() -> mock.MagicMock:
    return mock.MagicMock()


@pytest.fixture(name="build_subscription")
def _build_subscription(
    user_id: str,
    bank_account_id: uuid.UUID,
) -> SubscriptionBuilder:
    """Return a builder for subscriptions, overridable field by field."""

    def _build(  # noqa: PLR0913
        *,
        name: str = _DEFAULT_NAME,
        amount: float = _DEFAULT_AMOUNT,
        cadence: Cadence = "monthly",
        start_date: datetime.date = datetime.date(2026, 1, 1),
        end_date: datetime.date | None = None,
        is_active: bool = True,
        category_id: uuid.UUID | None = None,
        sub_id: uuid.UUID | None = None,
    ) -> entities.SubscriptionModel:
        return entities.SubscriptionModel(
            id=sub_id or uuid.uuid4(),
            user_id=user_id,
            name=name,
            amount=amount,
            cadence=cadence,
            bank_account_id=bank_account_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
        )

    return _build


@pytest.fixture(name="build_payment")
def _build_payment() -> PaymentBuilder:
    """Return a builder for the payments a subscription has already generated."""

    def _build(
        sub: entities.SubscriptionModel,
        payment_date: datetime.date,
        *,
        payment_id: uuid.UUID | None = None,
    ) -> entities.ExpensePaymentModel:
        return entities.ExpensePaymentModel(
            id=payment_id or uuid.uuid4(),
            user_id=sub.user_id,
            name=f"Sub: {sub.name}",
            expense=sub.amount,
            payment_date=payment_date,
            bank_account_id=sub.bank_account_id,
            category_id=sub.category_id,
            subscription_id=sub.id,
        )

    return _build


@pytest.fixture(name="build_use_case")
def _build_use_case(
    mock_subscription_repo: mock.MagicMock,
    mock_payment_repo: mock.MagicMock,
) -> UseCaseBuilder:
    """Return a builder for the use case, letting a test move its reference date."""

    def _build(*, today: datetime.date = _TODAY) -> ReconcileSubscriptionsUseCase:
        return ReconcileSubscriptionsUseCase(
            subscription_repo=mock_subscription_repo,
            payment_repo=mock_payment_repo,
            today=today,
        )

    return _build


@pytest.fixture(name="use_case")
def _use_case(build_use_case: UseCaseBuilder) -> ReconcileSubscriptionsUseCase:
    return build_use_case()


class TestReconcileSubscription:
    """Tests for _reconcile_subscription."""

    @pytest.mark.parametrize(
        ("cadence", "start_date", "expected_date"),
        [
            pytest.param(
                "weekly",
                datetime.date(2026, 4, 27),
                datetime.date(2026, 5, 4),
                id="weekly",
            ),
            pytest.param(
                "biannually",
                datetime.date(2025, 11, 4),
                datetime.date(2026, 5, 4),
                id="biannually",
            ),
            pytest.param(
                "monthly",
                datetime.date(2026, 1, 1),
                datetime.date(2026, 6, 1),
                id="monthly",
            ),
            pytest.param(
                "quarterly",
                datetime.date(2026, 1, 1),
                datetime.date(2026, 7, 1),
                id="quarterly",
            ),
            pytest.param(
                "yearly",
                datetime.date(2026, 1, 1),
                datetime.date(2027, 1, 1),
                id="yearly",
            ),
        ],
    )
    def test_active_sub_no_future_payment_creates_one(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        cadence: Cadence,
        start_date: datetime.date,
        expected_date: datetime.date,
    ) -> None:
        # Arrange
        sub = build_subscription(cadence=cadence, start_date=start_date)

        # Act
        new_rows, _ = use_case._reconcile_subscription(sub, [])

        # Assert
        assert all(
            [
                len(new_rows) == 1,
                new_rows[0]["name"] == f"Sub: {_DEFAULT_NAME}",
                new_rows[0]["expense"] == _DEFAULT_AMOUNT,
                new_rows[0]["payment_date"] == expected_date,
            ],
        )

    @pytest.mark.parametrize(
        ("sub_kwargs", "payment_date"),
        [
            pytest.param({}, datetime.date(2099, 1, 1), id="active_sub_future_payment"),
            pytest.param(
                {"end_date": datetime.date(2099, 12, 31)},
                datetime.date(2099, 6, 1),
                id="future_payment_before_end_date",
            ),
        ],
    )
    def test_valid_future_payment_is_kept(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
        sub_kwargs: dict,
        payment_date: datetime.date,
    ) -> None:
        # Arrange
        sub = build_subscription(**sub_kwargs)
        payment = build_payment(sub, payment_date)

        # Act
        new_rows, deleted_ids = use_case._reconcile_subscription(sub, [payment])

        # Assert
        assert all(
            [
                len(new_rows) == 0,
                len(deleted_ids) == 0,
            ],
        )

    @pytest.mark.parametrize(
        ("sub_kwargs", "payment_date"),
        [
            pytest.param(
                {"is_active": False},
                datetime.date(2099, 1, 1),
                id="inactive_sub",
            ),
            pytest.param(
                {"end_date": datetime.date(2026, 6, 1)},
                datetime.date(2026, 7, 1),
                id="payment_past_end_date",
            ),
        ],
    )
    def test_invalid_future_payment_is_deleted(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
        sub_kwargs: dict,
        payment_date: datetime.date,
    ) -> None:
        # Arrange
        sub = build_subscription(**sub_kwargs)
        payment = build_payment(sub, payment_date)

        # Act
        _, deleted_ids = use_case._reconcile_subscription(sub, [payment])

        # Assert
        assert all(
            [
                len(deleted_ids) == 1,
                str(payment.id) in deleted_ids,
            ],
        )

    @pytest.mark.parametrize(
        ("sub_kwargs", "payment_dates"),
        [
            pytest.param(
                {"is_active": False},
                [datetime.date(2020, 1, 1)],
                id="inactive_sub_past_payment",
            ),
            pytest.param(
                {
                    "start_date": datetime.date(2025, 1, 1),
                    "end_date": datetime.date(2025, 6, 1),
                },
                [],
                id="expired_sub_no_payments",
            ),
        ],
    )
    def test_no_action_taken(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
        sub_kwargs: dict,
        payment_dates: list[datetime.date],
    ) -> None:
        # Arrange
        sub = build_subscription(**sub_kwargs)
        payments = [build_payment(sub, date) for date in payment_dates]

        # Act
        new_rows, deleted_ids = use_case._reconcile_subscription(sub, payments)

        # Assert
        assert all(
            [
                len(new_rows) == 0,
                len(deleted_ids) == 0,
            ],
        )

    def test_created_payment_has_correct_subscription_id(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        bank_account_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> None:
        # Arrange
        sub = build_subscription(category_id=category_id)

        # Act
        new_rows, _ = use_case._reconcile_subscription(sub, [])

        # Assert
        added = new_rows[0]
        assert all(
            [
                added["subscription_id"] == sub.id,
                added["bank_account_id"] == bank_account_id,
                added["category_id"] == category_id,
                added["payment_type"] == "expense",
            ],
        )


class TestSettledCycleScheduling:
    """A payment re-dated to when the money actually moved still settles its cycle.

    Each payment is attributed to the scheduled date it lies closest to, so a
    charge nudged either side of its due date neither duplicates that cycle nor
    swallows the following one.
    """

    @pytest.mark.parametrize(
        ("sub_kwargs", "today", "payment_date", "expected_dates"),
        [
            pytest.param(
                {"start_date": datetime.date(2026, 1, 6)},
                datetime.date(2026, 5, 4),
                datetime.date(2026, 5, 3),
                [datetime.date(2026, 6, 6)],
                id="redated_earlier_rolls_on_instead_of_duplicating",
            ),
            pytest.param(
                {"start_date": datetime.date(2026, 1, 6)},
                datetime.date(2026, 5, 4),
                datetime.date(2026, 4, 6),
                [datetime.date(2026, 5, 6)],
                id="previous_cycle_payment_leaves_current_due",
            ),
            pytest.param(
                {"start_date": datetime.date(2026, 1, 6)},
                datetime.date(2026, 5, 12),
                datetime.date(2026, 5, 9),
                [datetime.date(2026, 6, 6)],
                id="redated_later_settles_its_own_cycle_only",
            ),
            pytest.param(
                {"start_date": datetime.date(2026, 4, 29), "cadence": "weekly"},
                datetime.date(2026, 5, 4),
                datetime.date(2026, 5, 3),
                [datetime.date(2026, 5, 13)],
                id="tolerance_scales_to_a_weekly_cadence",
            ),
            pytest.param(
                {
                    "start_date": datetime.date(2026, 1, 6),
                    "end_date": datetime.date(2026, 5, 31),
                },
                datetime.date(2026, 5, 4),
                datetime.date(2026, 5, 3),
                [],
                id="settled_cycle_past_end_date_creates_nothing",
            ),
        ],
    )
    def test_schedules_from_the_first_unsettled_cycle(  # noqa: PLR0913
        self,
        build_use_case: UseCaseBuilder,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
        sub_kwargs: dict,
        today: datetime.date,
        payment_date: datetime.date,
        expected_dates: list[datetime.date],
    ) -> None:
        # Arrange
        use_case = build_use_case(today=today)
        sub = build_subscription(**sub_kwargs)
        payment = build_payment(sub, payment_date)

        # Act
        new_rows, deleted_ids = use_case._reconcile_subscription(sub, [payment])

        # Assert
        assert all(
            [
                [row["payment_date"] for row in new_rows] == expected_dates,
                len(deleted_ids) == 0,
            ],
        )

    def test_execute_does_not_duplicate_a_redated_payment(
        self,
        build_use_case: UseCaseBuilder,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
        mock_subscription_repo: mock.MagicMock,
        mock_payment_repo: mock.MagicMock,
    ) -> None:
        # Arrange - the payment due on the 6th, moved back to the 3rd it left on
        sub = build_subscription(start_date=datetime.date(2026, 1, 6))
        payment = build_payment(sub, datetime.date(2026, 5, 3))
        mock_subscription_repo.get_all.return_value = [sub]
        mock_payment_repo.get_all.return_value = [payment]
        use_case = build_use_case(today=datetime.date(2026, 5, 4))

        # Act
        use_case.execute()

        # Assert - the settled cycle is not rebooked on the 6th
        written = mock_payment_repo.build_entities.call_args.args[0]
        assert [row["payment_date"] for row in written] == [datetime.date(2026, 6, 6)]


class TestComputeNextDate:
    """Tests for _compute_next_date."""

    @pytest.mark.parametrize(
        ("sub_kwargs", "expected"),
        [
            pytest.param(
                {"cadence": "weekly", "start_date": datetime.date(2026, 4, 27)},
                datetime.date(2026, 5, 4),
                id="weekly_past",
            ),
            pytest.param(
                {"cadence": "biannually", "start_date": datetime.date(2025, 11, 4)},
                datetime.date(2026, 5, 4),
                id="biannually_past",
            ),
            pytest.param(
                {"cadence": "monthly", "start_date": datetime.date(2026, 1, 1)},
                datetime.date(2026, 6, 1),
                id="monthly_past",
            ),
            pytest.param(
                {"cadence": "quarterly", "start_date": datetime.date(2026, 1, 1)},
                datetime.date(2026, 7, 1),
                id="quarterly_past",
            ),
            pytest.param(
                {"cadence": "yearly", "start_date": datetime.date(2025, 12, 1)},
                datetime.date(2026, 12, 1),
                id="yearly_past",
            ),
            pytest.param({"start_date": _TODAY}, _TODAY, id="start_date_is_today"),
            pytest.param({"start_date": _FUTURE}, _FUTURE, id="start_date_in_future"),
        ],
    )
    def test_returns_expected_date(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        sub_kwargs: dict,
        expected: datetime.date,
    ) -> None:
        # Arrange
        sub = build_subscription(**sub_kwargs)

        # Act / Assert
        assert use_case._compute_next_date(sub) == expected

    @pytest.mark.parametrize(
        "sub_kwargs",
        [
            pytest.param(
                {
                    "start_date": datetime.date(2025, 1, 1),
                    "end_date": datetime.date(2025, 6, 1),
                },
                id="end_date_in_past",
            ),
            pytest.param(
                {
                    "cadence": "yearly",
                    "start_date": datetime.date(2025, 1, 1),
                    "end_date": datetime.date(2026, 6, 1),
                },
                id="next_date_exceeds_end_date",
            ),
        ],
    )
    def test_returns_none(
        self,
        use_case: ReconcileSubscriptionsUseCase,
        build_subscription: SubscriptionBuilder,
        sub_kwargs: dict,
    ) -> None:
        # Arrange
        sub = build_subscription(**sub_kwargs)

        # Act / Assert
        assert use_case._compute_next_date(sub) is None


class TestGroupPaymentsBySubscription:
    """Tests for _group_payments_by_subscription."""

    def test_groups_by_subscription_id(
        self,
        build_subscription: SubscriptionBuilder,
        build_payment: PaymentBuilder,
    ) -> None:
        # Arrange
        sub1 = build_subscription(name="Sub1")
        sub2 = build_subscription(name="Sub2")
        payments = [
            build_payment(sub1, datetime.date(2026, 6, 1)),
            build_payment(sub1, datetime.date(2026, 7, 1)),
            build_payment(sub2, datetime.date(2026, 6, 1)),
        ]

        # Act
        result = ReconcileSubscriptionsUseCase._group_payments_by_subscription(payments)

        # Assert
        expected_sub1_count = 2
        expected_sub2_count = 1
        assert all(
            [
                len(result[str(sub1.id)]) == expected_sub1_count,
                len(result[str(sub2.id)]) == expected_sub2_count,
            ],
        )

    def test_skips_payments_without_subscription_id(
        self,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        payment = entities.ExpensePaymentModel(
            user_id=user_id,
            name="Manual payment",
            expense=10.0,
            payment_date=datetime.date(2026, 6, 1),
            bank_account_id=bank_account_id,
            subscription_id=None,
        )

        # Act
        result = ReconcileSubscriptionsUseCase._group_payments_by_subscription(
            [payment],
        )

        # Assert
        assert len(result) == 0


class TestCadenceTranslation:
    """The use case translates an unknown cadence across layers."""

    def test_unknown_cadence_becomes_invalid_cadence_error_with_metadata(
        self,
        build_use_case: UseCaseBuilder,
        build_subscription: SubscriptionBuilder,
        mock_subscription_repo: mock.MagicMock,
        mock_payment_repo: mock.MagicMock,
    ) -> None:
        # Arrange - model_copy bypasses validation to drive a bad cadence into
        # the reconcile logic (the field itself is a validated Literal).
        sub = build_subscription().model_copy(update={"cadence": "fortnightly"})
        mock_subscription_repo.get_all.return_value = [sub]
        mock_payment_repo.get_all.return_value = []
        use_case = build_use_case()

        # Act
        with pytest.raises(InvalidCadenceError) as exc_info:
            use_case.execute()

        # Assert - the cadence is carried and the domain error is the chained cause
        assert all(
            [
                exc_info.value.cadence == "FORTNIGHTLY",
                isinstance(exc_info.value.__cause__, InvalidSubscriptionCadenceError),
            ],
        )
