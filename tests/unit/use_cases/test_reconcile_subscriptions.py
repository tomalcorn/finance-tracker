"""Unit tests for ReconcileSubscriptionsUseCase."""

import datetime
import typing
import uuid
from collections.abc import Callable
from unittest import mock

import pytest

from domain import entities
from use_cases.reconcile_subscriptions import ReconcileSubscriptionsUseCase

type Cadence = typing.Literal[
    "weekly",
    "monthly",
    "quarterly",
    "biannually",
    "yearly",
]


@pytest.fixture(name="user_id")
def _user_id() -> str:
    return "auth0|test-user-123"


@pytest.fixture(name="bank_account_id")
def _bank_account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(name="expense_source_id")
def _expense_source_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(name="mock_subscription_repo")
def _mock_subscription_repo() -> mock.MagicMock:
    return mock.MagicMock()


@pytest.fixture(name="mock_payment_repo")
def _mock_payment_repo() -> mock.MagicMock:
    return mock.MagicMock()


_DEFAULT_AMOUNT = 15.99
_DEFAULT_NAME = "Netflix"


def _make_subscription(  # noqa: PLR0913
    user_id: str,
    bank_account_id: uuid.UUID,
    *,
    name: str = _DEFAULT_NAME,
    amount: float = _DEFAULT_AMOUNT,
    cadence: Cadence = "monthly",
    start_date: datetime.date = datetime.date(2026, 1, 1),
    end_date: datetime.date | None = None,
    is_active: bool = True,
    expense_source_id: uuid.UUID | None = None,
    sub_id: uuid.UUID | None = None,
) -> entities.SubscriptionModel:
    return entities.SubscriptionModel(
        id=sub_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        amount=amount,
        cadence=cadence,
        bank_account_id=bank_account_id,
        expense_source_id=expense_source_id,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )


def _make_payment(
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
        expense_source_id=sub.expense_source_id,
        subscription_id=sub.id,
    )


def _use_case(
    mock_subscription_repo: mock.MagicMock,
    mock_payment_repo: mock.MagicMock,
    *,
    today: datetime.date | None = None,
) -> ReconcileSubscriptionsUseCase:
    return ReconcileSubscriptionsUseCase(
        subscription_repo=mock_subscription_repo,
        payment_repo=mock_payment_repo,
        today=today,
    )


class TestReconcileSubscription:
    """Tests for _reconcile_subscription."""

    _TODAY = datetime.date(2026, 5, 4)

    @pytest.fixture(autouse=True)
    def _setup_use_case(
        self,
        mock_subscription_repo: mock.MagicMock,
        mock_payment_repo: mock.MagicMock,
    ) -> None:
        self.use_case = _use_case(
            mock_subscription_repo,
            mock_payment_repo,
            today=self._TODAY,
        )

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
        user_id: str,
        bank_account_id: uuid.UUID,
        cadence: Cadence,
        start_date: datetime.date,
        expected_date: datetime.date,
    ) -> None:
        sub = _make_subscription(
            user_id,
            bank_account_id,
            cadence=cadence,
            start_date=start_date,
        )
        updates = entities.BackendUpdates()

        self.use_case._reconcile_subscription(sub, [], updates)

        assert all(
            [
                len(updates.added_rows) == 1,
                updates.added_rows[0]["name"] == f"Sub: {_DEFAULT_NAME}",
                updates.added_rows[0]["expense"] == _DEFAULT_AMOUNT,
                updates.added_rows[0]["payment_date"] == expected_date.isoformat(),
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
        user_id: str,
        bank_account_id: uuid.UUID,
        sub_kwargs: dict,
        payment_date: datetime.date,
    ) -> None:
        sub = _make_subscription(user_id, bank_account_id, **sub_kwargs)
        payment = _make_payment(sub, payment_date)
        updates = entities.BackendUpdates()

        self.use_case._reconcile_subscription(sub, [payment], updates)

        assert all(
            [
                len(updates.added_rows) == 0,
                len(updates.edited_rows) == 0,
                len(updates.deleted_rows) == 0,
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
        user_id: str,
        bank_account_id: uuid.UUID,
        sub_kwargs: dict,
        payment_date: datetime.date,
    ) -> None:
        sub = _make_subscription(user_id, bank_account_id, **sub_kwargs)
        payment = _make_payment(sub, payment_date)
        updates = entities.BackendUpdates()

        self.use_case._reconcile_subscription(sub, [payment], updates)

        assert all(
            [
                len(updates.deleted_rows) == 1,
                str(payment.id) in updates.deleted_rows,
            ],
        )

    @pytest.mark.parametrize(
        ("sub_kwargs", "payments_factory"),
        [
            pytest.param(
                {"is_active": False},
                lambda sub: [_make_payment(sub, datetime.date(2020, 1, 1))],
                id="inactive_sub_past_payment",
            ),
            pytest.param(
                {
                    "start_date": datetime.date(2025, 1, 1),
                    "end_date": datetime.date(2025, 6, 1),
                },
                lambda _sub: [],
                id="expired_sub_no_payments",
            ),
        ],
    )
    def test_no_action_taken(
        self,
        user_id: str,
        bank_account_id: uuid.UUID,
        sub_kwargs: dict,
        payments_factory: Callable[
            [entities.SubscriptionModel],
            list[entities.ExpensePaymentModel],
        ],
    ) -> None:
        sub = _make_subscription(user_id, bank_account_id, **sub_kwargs)
        payments = payments_factory(sub)
        updates = entities.BackendUpdates()

        self.use_case._reconcile_subscription(sub, payments, updates)

        assert all(
            [
                len(updates.added_rows) == 0,
                len(updates.deleted_rows) == 0,
            ],
        )

    def test_created_payment_has_correct_subscription_id(
        self,
        user_id: str,
        bank_account_id: uuid.UUID,
        expense_source_id: uuid.UUID,
    ) -> None:
        sub = _make_subscription(
            user_id,
            bank_account_id,
            expense_source_id=expense_source_id,
        )
        updates = entities.BackendUpdates()

        self.use_case._reconcile_subscription(sub, [], updates)

        added = updates.added_rows[0]
        assert all(
            [
                added["subscription_id"] == str(sub.id),
                added["bank_account_id"] == str(bank_account_id),
                added["expense_source_id"] == str(expense_source_id),
                added["payment_type"] == "expense",
            ],
        )


class TestComputeNextDate:
    """Tests for _compute_next_date."""

    _TODAY = datetime.date(2026, 5, 4)
    _FUTURE = _TODAY + datetime.timedelta(days=30)

    @pytest.fixture(autouse=True)
    def _setup_use_case(
        self,
        mock_subscription_repo: mock.MagicMock,
        mock_payment_repo: mock.MagicMock,
    ) -> None:
        """Set use case's reference date to a fixed value for deterministic tests."""
        self.use_case = _use_case(
            mock_subscription_repo,
            mock_payment_repo,
            today=self._TODAY,
        )

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
        user_id: str,
        bank_account_id: uuid.UUID,
        sub_kwargs: dict,
        expected: datetime.date,
    ) -> None:
        sub = _make_subscription(user_id, bank_account_id, **sub_kwargs)
        assert self.use_case._compute_next_date(sub) == expected

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
        user_id: str,
        bank_account_id: uuid.UUID,
        sub_kwargs: dict,
    ) -> None:
        sub = _make_subscription(user_id, bank_account_id, **sub_kwargs)
        assert self.use_case._compute_next_date(sub) is None


class TestGroupPaymentsBySubscription:
    """Tests for _group_payments_by_subscription."""

    def test_groups_by_subscription_id(
        self,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        sub1 = _make_subscription(user_id, bank_account_id, name="Sub1")
        sub2 = _make_subscription(user_id, bank_account_id, name="Sub2")
        payments = [
            _make_payment(sub1, datetime.date(2026, 6, 1)),
            _make_payment(sub1, datetime.date(2026, 7, 1)),
            _make_payment(sub2, datetime.date(2026, 6, 1)),
        ]

        result = ReconcileSubscriptionsUseCase._group_payments_by_subscription(payments)

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
        payment = entities.ExpensePaymentModel(
            user_id=user_id,
            name="Manual payment",
            expense=10.0,
            payment_date=datetime.date(2026, 6, 1),
            bank_account_id=bank_account_id,
            subscription_id=None,
        )

        result = ReconcileSubscriptionsUseCase._group_payments_by_subscription(
            [payment],
        )

        assert len(result) == 0
