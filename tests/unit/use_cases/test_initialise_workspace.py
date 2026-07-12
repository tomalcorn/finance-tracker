"""Tests for InitializeUserWorkspaceUseCase."""

import uuid

import pytest

from domain import entities
from ports import repository
from use_cases import errors, initialise_workspace

# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeRepository[E: entities.FinanceTrackerBaseModel](repository.Repository[E]):
    """In-memory Repository fake with a save-failure switch for error tests."""

    def __init__(self, items: list[E] | None = None) -> None:
        """Seed the fake with initial items."""
        self._items: dict[uuid.UUID, E] = {item.id: item for item in (items or [])}
        self.saved: list[E] = []
        self.raise_on_save = False

    def get_all(self) -> list[E]:
        return list(self._items.values())

    def get_by_id(self, item_id: uuid.UUID) -> E | None:
        return self._items.get(item_id)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        return [self._items[i] for i in ids if i in self._items]

    def save(self, item: E) -> None:
        if self.raise_on_save:
            msg = "Simulated save failure"
            raise RuntimeError(msg)
        self._items[item.id] = item
        self.saved.append(item)

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; workspace initialisation saves one row at a time."""


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

USER_ID = "user-abc"
ALL_BT_NAMES = set(entities.BudgetTrackerName)
HIDDEN_BT_NAMES = {
    entities.BudgetTrackerName.JOINT,
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
}


def make_use_case(
    existing_trackers: list[entities.BudgetTrackerItemModel] | None = None,
    existing_sources: list[entities.ExpenseSourceModel] | None = None,
) -> tuple[
    initialise_workspace.InitialiseUserWorkspaceUseCase,
    FakeRepository[entities.BudgetTrackerItemModel],
    FakeRepository[entities.ExpenseSourceModel],
]:
    bt_repo: FakeRepository[entities.BudgetTrackerItemModel] = FakeRepository(
        existing_trackers,
    )
    es_repo: FakeRepository[entities.ExpenseSourceModel] = FakeRepository(
        existing_sources,
    )
    use_case = initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=USER_ID,
        budget_tracker_repo=bt_repo,
        expense_source_repo=es_repo,
    )
    return use_case, bt_repo, es_repo


def make_tracker(name: entities.BudgetTrackerName) -> entities.BudgetTrackerItemModel:
    return entities.BudgetTrackerItemModel(user_id=USER_ID, name=name)


def make_all_trackers() -> list[entities.BudgetTrackerItemModel]:
    return [make_tracker(name) for name in entities.BudgetTrackerName]


# ---------------------------------------------------------------------------
# Budget tracker seeding
# ---------------------------------------------------------------------------


def test_all_budget_tracker_names_are_created_for_a_fresh_user_with_correct_user_id():
    # Arrange
    use_case, bt_repo, _ = make_use_case()

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert all(
        [
            created_names == ALL_BT_NAMES,
            all(bt.user_id == USER_ID for bt in bt_repo.get_all()),
        ],
    )


def test_no_budget_trackers_are_duplicated_when_all_already_exist():
    # Arrange
    existing = make_all_trackers()
    use_case, bt_repo, _ = make_use_case(existing_trackers=existing)

    # Act
    use_case.execute()

    # Assert
    assert len(bt_repo.get_all()) == len(ALL_BT_NAMES)


@pytest.mark.parametrize(
    "missing_name",
    [pytest.param(name, id=name.value) for name in entities.BudgetTrackerName],
)
def test_missing_budget_tracker_is_created_when_others_exist(
    missing_name: entities.BudgetTrackerName,
) -> None:
    # Arrange
    existing = [
        make_tracker(n) for n in entities.BudgetTrackerName if n != missing_name
    ]
    use_case, bt_repo, _ = make_use_case(existing_trackers=existing)

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert missing_name in created_names


# ---------------------------------------------------------------------------
# Hidden expense source seeding
# ---------------------------------------------------------------------------


def test_hidden_expense_sources_created_for_each_hidden_bt_name_with_right_user_id():
    # Arrange
    use_case, _, es_repo = make_use_case()

    # Act
    use_case.execute()

    # Assert
    created_names = {es.name for es in es_repo.get_all()}
    assert all(
        [
            created_names == {name.value for name in HIDDEN_BT_NAMES},
            all(es.user_id == USER_ID for es in es_repo.get_all()),
        ],
    )


def test_hidden_expense_source_is_linked_to_its_budget_tracker():
    # Arrange
    use_case, bt_repo, es_repo = make_use_case()

    # Act
    use_case.execute()

    # Assert
    bt_id_by_name = {bt.name: bt.id for bt in bt_repo.get_all()}
    es_by_name = {es.name: es for es in es_repo.get_all()}

    assert all(
        bt_id_by_name[bt_name] in (es_by_name[bt_name.value].budget_tracker_ids or [])
        for bt_name in HIDDEN_BT_NAMES
    )


def test_no_expense_sources_are_duplicated_when_all_already_exist():
    # Arrange
    trackers = make_all_trackers()
    bt_id_by_name = {bt.name: bt.id for bt in trackers}
    existing_sources = [
        entities.ExpenseSourceModel(
            user_id=USER_ID,
            name=bt_name.value,
            budget_tracker_ids=[bt_id_by_name[bt_name]],
        )
        for bt_name in HIDDEN_BT_NAMES
    ]
    use_case, _, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=existing_sources,
    )

    # Act
    use_case.execute()

    # Assert
    assert len(es_repo.get_all()) == len(HIDDEN_BT_NAMES)


def test_existing_expense_source_with_missing_bt_id_gets_it_added():
    # Arrange
    trackers = make_all_trackers()
    bt_id_by_name = {bt.name: bt.id for bt in trackers}
    target_bt_name = entities.BudgetTrackerName.ONE_OFFS

    # Source exists but is not yet linked to the tracker
    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=[],
    )
    use_case, _, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert
    updated = es_repo.get_by_id(existing_source.id)
    assert updated is not None
    assert bt_id_by_name[target_bt_name] in (updated.budget_tracker_ids or [])


def test_existing_expense_source_with_none_bt_ids_gets_bt_id_set():
    # Arrange
    trackers = make_all_trackers()
    target_bt_name = entities.BudgetTrackerName.SAVINGS

    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
    )
    use_case, bt_repo, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert
    bt_id = next(bt.id for bt in bt_repo.get_all() if bt.name == target_bt_name)
    updated = es_repo.get_by_id(existing_source.id)
    assert updated is not None
    assert bt_id in (updated.budget_tracker_ids or [])


def test_existing_expense_source_with_none_bt_ids_is_persisted():
    # Arrange - the None-branch mutates the source, so it must also save it back;
    # otherwise the link is only set in memory and dropped (issue #146).
    trackers = make_all_trackers()
    target_bt_name = entities.BudgetTrackerName.SAVINGS
    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
    )
    use_case, _, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert - the mutated source is written back, not just changed in memory
    assert existing_source in es_repo.saved


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_repository_failure_raises_data_access_error():
    # Arrange
    use_case, bt_repo, _ = make_use_case()
    bt_repo.raise_on_save = True

    # Act
    with pytest.raises(errors.DataAccessError) as exc_info:
        use_case.execute()

    # Assert - the user id is in the message and the underlying failure is chained
    assert all(
        [
            USER_ID in str(exc_info.value),
            isinstance(exc_info.value.__cause__, RuntimeError),
        ],
    )
