"""Tests for BankOneOffsUseCase."""

import datetime
import uuid

import pytest

from domain import entities
from ports import repository
from use_cases.bank_one_offs import BankOneOffsUseCase
from use_cases.errors import AmountToBankLTEZeroError

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeOneOffRepository(repository.OneOffRepository):
    def __init__(self, items: list[entities.OneOffItemModel]) -> None:
        """Construct FakeOneOffRepository."""
        self._items = {item.id: item for item in items}

    def get_by_id(self, item_id: uuid.UUID) -> entities.OneOffItemModel | None:
        """Return a single one-off item, or None if not found."""

    def get_by_ids(self, item_ids: list[uuid.UUID]) -> list[entities.OneOffItemModel]:
        return [self._items[i] for i in item_ids if i in self._items]

    def get_all(self) -> list[entities.OneOffItemModel]:
        return list(self._items.values())

    def save(self, item: entities.OneOffItemModel) -> None:
        self._items[item.id] = item

    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a one-off item by ID."""


class FakeBudgetTrackerRepository(repository.BudgetTrackerRepository):
    def __init__(self, items: list[entities.BudgetTrackerItemModel]) -> None:
        """Construct FakeBudgetTrackerRepository."""
        self._items = items

    def get_all(self) -> list[entities.BudgetTrackerItemModel]:
        return self._items

    def get_by_id(self, item_id: uuid.UUID) -> entities.BudgetTrackerItemModel | None:
        """Return a single budget tracker item, or None if not found."""

    def get_by_ids(
        self,
        item_ids: list[uuid.UUID],  # noqa: ARG002 - not needed for stub
    ) -> list[entities.BudgetTrackerItemModel]:
        """Return budget tracker items matching the given IDs."""
        return []

    def save(self, item: entities.BudgetTrackerItemModel) -> None:
        """Insert or update a budget tracker item."""

    def save_many(self, items: list[entities.BudgetTrackerItemModel]) -> None:
        """Insert or update multiple budget tracker items in one operation.

        Used by InitializeUserWorkspaceUseCase to seed default trackers.
        """

    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a budget tracker item by ID."""


class FakeExpenseSourceRepository(repository.ExpenseSourceRepository):
    def __init__(self, sources: list[entities.ExpenseSourceModel]) -> None:
        """Construct FakeExpenseSourceRepository."""
        self._sources = sources

    def get_all(self) -> list[entities.ExpenseSourceModel]:
        return self._sources

    def get_by_id(self, source_id: uuid.UUID) -> entities.ExpenseSourceModel | None:
        """Return a single expense source, or None if not found."""

    def save(self, source: entities.ExpenseSourceModel) -> None:
        """Insert or update an expense source."""

    def delete(self, source_id: uuid.UUID) -> None:
        """Delete an expense source by ID."""


class FakePaymentRepository(repository.PaymentRepository):
    def __init__(self) -> None:
        """Construct FakePaymentRepository."""
        self.saved: list[entities.AnyPaymentModel] = []

    def get_all(self) -> list[entities.AnyPaymentModel]:
        """Return all payments (expense and income) for the current user."""
        return []

    def get_by_bank_account(
        self,
        bank_account_id: uuid.UUID,  # noqa: ARG002 - not needed for test
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments associated with a specific bank account.

        Used when banking one-offs to find existing payments for the account.
        """
        return []

    def get_by_subscription(
        self,
        subscription_id: uuid.UUID,  # noqa: ARG002 - not needed for test
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments generated from a specific subscription.

        Used by ReconcileSubscriptionsUseCase to determine whether future
        payments already exist.
        """
        return []

    def save(self, payment: entities.AnyPaymentModel) -> None:
        self.saved.append(payment)

    def save_many(self, payments: list[entities.AnyPaymentModel]) -> None:
        """Insert or update multiple payments in one operation.

        Used by ReconcileSubscriptionsUseCase to bulk-create future payments.
        """

    def apply_updates(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of payment inserts and deletes in one operation.

        Used by ReconcileSubscriptionsUseCase to persist reconciliation
        changes atomically and invalidate dependent view caches.
        """

    def delete(self, payment_id: uuid.UUID) -> None:
        """Delete a payment by ID."""


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

USER_ID = "user-123"
BANK_ACCOUNT_ID = uuid.uuid4()
PAYMENT_DATE = datetime.date(2025, 1, 1)


def _make_one_off(
    *,
    current_month: float = 50.0,
    banked: float = 0.0,
    name: str = "Holiday",
) -> entities.OneOffItemModel:
    return entities.OneOffItemModel(
        user_id=USER_ID,
        name=name,
        current_month=current_month,
        banked=banked,
    )


def _make_one_offs_tracker() -> entities.BudgetTrackerItemModel:
    return entities.BudgetTrackerItemModel(
        user_id=USER_ID,
        name=entities.BudgetTrackerName.ONE_OFFS,
    )


def _make_expense_source(
    budget_tracker_ids: list[uuid.UUID] | None = None,
) -> entities.ExpenseSourceModel:
    return entities.ExpenseSourceModel(
        user_id=USER_ID,
        name="One-offs source",
        budget_tracker_ids=budget_tracker_ids,
    )


def _make_use_case(
    items: list[entities.OneOffItemModel],
    budget_trackers: list[entities.BudgetTrackerItemModel] | None = None,
    expense_sources: list[entities.ExpenseSourceModel] | None = None,
    payment_repo: FakePaymentRepository | None = None,
) -> tuple[BankOneOffsUseCase, FakeOneOffRepository, FakePaymentRepository]:
    one_off_repo = FakeOneOffRepository(items)
    bt_repo = FakeBudgetTrackerRepository(budget_trackers or [])
    es_repo = FakeExpenseSourceRepository(expense_sources or [])
    p_repo = payment_repo or FakePaymentRepository()
    use_case = BankOneOffsUseCase(
        one_off_repo=one_off_repo,
        budget_tracker_repo=bt_repo,
        expense_source_repo=es_repo,
        payment_repo=p_repo,
    )
    return use_case, one_off_repo, p_repo


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_banking_an_item_zeroes_current_month_and_accumulates_banked():
    # Arrange
    item = _make_one_off(current_month=50.0, banked=100.0)
    use_case, one_off_repo, _ = _make_use_case([item])

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    saved = one_off_repo.get_all()[0]
    expected_banked = 150.0
    assert all(
        [
            saved.current_month == 0,
            saved.banked == expected_banked,
        ],
    )


def test_banking_an_item_creates_a_payment():
    # Arrange
    item = _make_one_off(current_month=50.0)
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case([item], payment_repo=payment_repo)

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    assert len(payment_repo.saved) == 1


def test_payment_fields_reflect_the_banked_item():
    # Arrange
    item = _make_one_off(current_month=50.0, name="Holiday")
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case([item], payment_repo=payment_repo)

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

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


def test_banking_multiple_items_creates_one_payment_per_item():
    # Arrange
    items = [
        _make_one_off(current_month=50.0, name="Holiday"),
        _make_one_off(current_month=30.0, name="Car"),
    ]
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case(items, payment_repo=payment_repo)

    # Act
    use_case.execute([i.id for i in items], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    expected_saved = 2
    assert len(payment_repo.saved) == expected_saved


def test_payment_uses_current_month_not_post_update_banked():
    """Ensures the payment amount is the monthly contribution, not the running total."""
    # Arrange
    item = _make_one_off(current_month=50.0, banked=200.0)
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case([item], payment_repo=payment_repo)

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    expected_paid = 50.0
    assert payment_repo.saved[0].expense == expected_paid


# ---------------------------------------------------------------------------
# Expense source resolution
# ---------------------------------------------------------------------------


def test_payment_has_expense_source_id_when_one_offs_tracker_and_source_exist():
    # Arrange
    tracker = _make_one_offs_tracker()
    source = _make_expense_source(budget_tracker_ids=[tracker.id])
    item = _make_one_off(current_month=50.0)
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case(
        [item],
        budget_trackers=[tracker],
        expense_sources=[source],
        payment_repo=payment_repo,
    )

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    payment = payment_repo.saved[0]
    assert isinstance(payment, entities.ExpensePaymentModel)
    assert payment.expense_source_id == source.id


@pytest.mark.parametrize(
    ("budget_trackers", "expense_sources"),
    [
        pytest.param([], [], id="no_budget_trackers"),
        pytest.param([_make_one_offs_tracker()], [], id="tracker_exists_but_no_source"),
    ],
)
def test_payment_expense_source_id_is_none_when_lookup_cannot_resolve(
    budget_trackers: list[entities.BudgetTrackerItemModel],
    expense_sources: list[entities.ExpenseSourceModel],
):
    # Arrange
    item = _make_one_off(current_month=50.0)
    payment_repo = FakePaymentRepository()
    use_case, _, _ = _make_use_case(
        [item],
        budget_trackers=budget_trackers,
        expense_sources=expense_sources,
        payment_repo=payment_repo,
    )

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    payment = payment_repo.saved[0]
    assert isinstance(payment, entities.ExpensePaymentModel)
    assert payment.expense_source_id is None


# ---------------------------------------------------------------------------
# Business rule violations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current_month", "expected_match"),
    [
        pytest.param(0.0, "Holiday", id="zero"),
        pytest.param(-10.0, "Car", id="negative"),
    ],
)
def test_banking_item_with_non_positive_amount_raises(
    current_month: float,
    expected_match: str,
):
    # Arrange
    item = _make_one_off(current_month=current_month, name=expected_match)
    use_case, _, _ = _make_use_case([item])

    # Act / Assert
    with pytest.raises(AmountToBankLTEZeroError, match=expected_match):
        use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)


def test_good_items_are_saved_if_any_item_has_non_positive_amount():
    # Arrange
    good_item = _make_one_off(current_month=50.0, name="Holiday")
    bad_item = _make_one_off(current_month=0.0, name="Car")
    use_case, one_off_repo, payment_repo = _make_use_case([good_item, bad_item])

    # Act
    with pytest.raises(AmountToBankLTEZeroError):
        use_case.execute([good_item.id, bad_item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert — good_item was processed before the error, so this test documents
    # the current behaviour: partial writes DO occur. Update this test if you
    # introduce a transaction / rollback mechanism.
    assert all(
        [
            one_off_repo.get_all()[0].current_month == 0,  # good_item was saved
            len(payment_repo.saved) == 1,  # its payment was created
        ],
    )
