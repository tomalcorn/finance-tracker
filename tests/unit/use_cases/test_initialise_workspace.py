"""Tests for InitializeUserWorkspaceUseCase."""

import uuid

import pytest

from domain import entities
from ports import repository
from use_cases import errors, initialise_workspace

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeBudgetTrackerRepository(repository.BudgetTrackerRepository):
    def __init__(
        self,
        items: list[entities.BudgetTrackerItemModel] | None = None,
    ) -> None:
        """Construct FakeBudgetTrackerRepository."""
        self._items: dict[uuid.UUID, entities.BudgetTrackerItemModel] = {
            item.id: item for item in (items or [])
        }
        self.raise_on_save = False

    def get_all(self) -> list[entities.BudgetTrackerItemModel]:
        return list(self._items.values())

    def get_by_id(self, item_id: uuid.UUID) -> entities.BudgetTrackerItemModel | None:
        return self._items.get(item_id)

    def get_by_ids(
        self,
        item_ids: list[uuid.UUID],
    ) -> list[entities.BudgetTrackerItemModel]:
        return [self._items[i] for i in item_ids if i in self._items]

    def save(self, item: entities.BudgetTrackerItemModel) -> None:
        if self.raise_on_save:
            msg = "Simulated save failure"
            raise RuntimeError(msg)
        self._items[item.id] = item

    def save_many(self, items: list[entities.BudgetTrackerItemModel]) -> None:
        for item in items:
            self.save(item)

    def delete(self, item_id: uuid.UUID) -> None:
        self._items.pop(item_id, None)

    def get_column_values(self, column_name: str) -> set[object]:
        """Return unique values for a column."""
        return {
            value
            for item in self._items.values()
            if (value := getattr(item, column_name, None)) is not None
        }


class FakeExpenseSourceRepository(repository.ExpenseSourceRepository):
    def __init__(
        self,
        sources: list[entities.ExpenseSourceModel] | None = None,
    ) -> None:
        """Construct FakeExpenseSourceRepository."""
        self._sources: dict[uuid.UUID, entities.ExpenseSourceModel] = {
            s.id: s for s in (sources or [])
        }
        self.raise_on_save = False

    def get_all(self) -> list[entities.ExpenseSourceModel]:
        return list(self._sources.values())

    def get_by_id(self, source_id: uuid.UUID) -> entities.ExpenseSourceModel | None:
        return self._sources.get(source_id)

    def save(self, source: entities.ExpenseSourceModel) -> None:
        if self.raise_on_save:
            msg = "Simulated save failure"
            raise RuntimeError(msg)
        self._sources[source.id] = source

    def delete(self, source_id: uuid.UUID) -> None:
        self._sources.pop(source_id, None)

    def get_column_values(self, column_name: str) -> set[object]:
        """Return unique values for a column."""
        return {
            value
            for source in self._sources.values()
            if (value := getattr(source, column_name, None)) is not None
        }


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
    FakeBudgetTrackerRepository,
    FakeExpenseSourceRepository,
]:
    bt_repo = FakeBudgetTrackerRepository(existing_trackers)
    es_repo = FakeExpenseSourceRepository(existing_sources)
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


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_repository_failure_raises_data_access_error():
    # Arrange
    use_case, bt_repo, _ = make_use_case()
    bt_repo.raise_on_save = True

    # Act / Assert
    with pytest.raises(errors.DataAccessError, match=USER_ID):
        use_case.execute()
