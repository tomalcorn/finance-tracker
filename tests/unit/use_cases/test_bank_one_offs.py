"""Tests for BankOneOffsUseCase."""

import datetime
import uuid

import pytest

from domain import entities
from ports import repository
from use_cases.bank_one_offs import BankOneOffsUseCase
from use_cases.errors import AmountToBankLTEZeroError

# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeRepository[E: entities.FinanceTrackerBaseModel](repository.Repository[E]):
    """In-memory Repository fake for use-case tests."""

    def __init__(self, items: list[E] | None = None) -> None:
        """Seed the fake with initial items."""
        self._items: dict[uuid.UUID, E] = {item.id: item for item in (items or [])}
        self.saved: list[E] = []
        self.applied: list[entities.BackendUpdates] = []

    def get_all(self) -> list[E]:
        return list(self._items.values())

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        return [self._items[i] for i in ids if i in self._items]

    def save(self, item: E) -> None:
        self._items[item.id] = item
        self.saved.append(item)

    def apply(self, updates: entities.BackendUpdates) -> None:
        self.applied.append(updates)


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
    payment_repo: FakeRepository[entities.AnyPaymentModel] | None = None,
) -> tuple[
    BankOneOffsUseCase,
    FakeRepository[entities.OneOffItemModel],
    FakeRepository[entities.AnyPaymentModel],
]:
    one_off_repo: FakeRepository[entities.OneOffItemModel] = FakeRepository(items)
    bt_repo: FakeRepository[entities.BudgetTrackerItemModel] = FakeRepository(
        budget_trackers or [],
    )
    es_repo: FakeRepository[entities.ExpenseSourceModel] = FakeRepository(
        expense_sources or [],
    )
    p_repo = payment_repo or FakeRepository[entities.AnyPaymentModel]()
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


def test_banked_one_off_is_persisted():
    # Arrange - the one-off is fetched, mutated, then saved back; saving an
    # existing row must reach the repository (issue #146).
    item = _make_one_off(current_month=50.0)
    use_case, one_off_repo, _ = _make_use_case([item])

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert - the existing row is written back through save
    assert item in one_off_repo.saved


def test_banking_an_item_creates_a_payment():
    # Arrange
    item = _make_one_off(current_month=50.0)
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
    use_case, _, _ = _make_use_case([item], payment_repo=payment_repo)

    # Act
    use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert
    assert len(payment_repo.saved) == 1


def test_payment_fields_reflect_the_banked_item():
    # Arrange
    item = _make_one_off(current_month=50.0, name="Holiday")
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
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
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
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
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
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
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
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
    payment_repo = FakeRepository[entities.AnyPaymentModel]()
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

    # Act
    with pytest.raises(AmountToBankLTEZeroError) as exc_info:
        use_case.execute([item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert - the offending item name is carried as metadata and in the message
    assert all(
        [
            exc_info.value.item_name == expected_match,
            expected_match in str(exc_info.value),
        ],
    )


def test_no_items_are_saved_if_any_item_has_non_positive_amount():
    # Arrange
    good_item = _make_one_off(current_month=50.0, name="Holiday")
    bad_item = _make_one_off(current_month=0.0, name="Car")
    use_case, one_off_repo, payment_repo = _make_use_case([good_item, bad_item])

    # Act
    with pytest.raises(AmountToBankLTEZeroError):
        use_case.execute([good_item.id, bad_item.id], BANK_ACCOUNT_ID, PAYMENT_DATE)

    # Assert — all items are validated before any are mutated, so a single bad
    # item aborts the whole batch with no partial writes.
    unchanged_current_month = 50.0
    saved_good_item = one_off_repo.get_all()[0]
    assert all(
        [
            saved_good_item.current_month == unchanged_current_month,
            saved_good_item.banked == 0.0,
            len(payment_repo.saved) == 0,
        ],
    )
