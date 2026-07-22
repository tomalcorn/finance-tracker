"""Tests for InitialiseJointWorkspaceUseCase."""

import uuid

import pytest

from domain import entities
from ports import errors as port_errors
from ports import repository
from use_cases import errors, initialise_joint_workspace

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRepository[E: entities.FinanceTrackerBaseModel](repository.Repository[E]):
    """In-memory Repository fake with a save-failure switch for error tests."""

    def __init__(self, items: list[E] | None = None) -> None:
        """Seed the fake with initial items."""
        self._items: dict[uuid.UUID, E] = {item.id: item for item in (items or [])}
        self.saved: list[E] = []
        self.raise_on_save = False
        self.unexpected_error: Exception | None = None

    def get_all(self) -> list[E]:
        return list(self._items.values())

    def get_by_id(self, item_id: uuid.UUID) -> E | None:
        return self._items.get(item_id)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        return [self._items[i] for i in ids if i in self._items]

    def save(self, item: E) -> None:
        if self.unexpected_error is not None:
            raise self.unexpected_error
        if self.raise_on_save:
            msg = "Simulated save failure"
            raise port_errors.RepositoryError(msg)
        self._items[item.id] = item
        self.saved.append(item)

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; workspace initialisation saves one row at a time."""


class FakeJointAccountRepo(repository.Repository[entities.JointAccountModel]):
    """Joint-accounts fake returning a preset membership for the current user."""

    def __init__(self, accounts: list[entities.JointAccountModel]) -> None:
        """Seed the fake with the accounts the user belongs to."""
        self._accounts = accounts

    def get_all(self) -> list[entities.JointAccountModel]:
        return list(self._accounts)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[entities.JointAccountModel]:
        id_set = set(ids)
        return [a for a in self._accounts if a.id in id_set]

    def save(self, item: entities.JointAccountModel) -> None:
        """No-op; the use case never writes joint accounts."""

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; the use case never writes joint accounts."""


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

USER_ID = "user-abc"
JOINT_ACCOUNT_ID = uuid.uuid4()

# The joint seed creates every budget tracker except JOINT.
JOINT_BT_NAMES = {
    name
    for name in entities.BudgetTrackerName
    if name is not entities.BudgetTrackerName.JOINT
}
# Hidden expense sources on the joint side: the personal hidden set minus JOINT.
JOINT_HIDDEN_BT_NAMES = {
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
}


def make_use_case(
    existing_trackers: list[entities.BudgetTrackerItemModel] | None = None,
    existing_sources: list[entities.ExpenseSourceModel] | None = None,
    *,
    accounts: list[entities.JointAccountModel] | None = None,
) -> tuple[
    initialise_joint_workspace.InitialiseJointWorkspaceUseCase,
    FakeRepository[entities.BudgetTrackerItemModel],
    FakeRepository[entities.ExpenseSourceModel],
]:
    bt_repo: FakeRepository[entities.BudgetTrackerItemModel] = FakeRepository(
        existing_trackers,
    )
    es_repo: FakeRepository[entities.ExpenseSourceModel] = FakeRepository(
        existing_sources,
    )
    if accounts is None:
        accounts = [entities.JointAccountModel(id=JOINT_ACCOUNT_ID, name="Ours")]
    use_case = initialise_joint_workspace.InitialiseJointWorkspaceUseCase(
        user_id=USER_ID,
        budget_tracker_repo=bt_repo,
        expense_source_repo=es_repo,
        joint_account_repo=FakeJointAccountRepo(accounts),
    )
    return use_case, bt_repo, es_repo


def make_tracker(name: entities.BudgetTrackerName) -> entities.BudgetTrackerItemModel:
    return entities.BudgetTrackerItemModel(
        user_id=USER_ID,
        name=name,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=JOINT_ACCOUNT_ID,
    )


def make_all_joint_trackers() -> list[entities.BudgetTrackerItemModel]:
    return [make_tracker(name) for name in JOINT_BT_NAMES]


# ---------------------------------------------------------------------------
# Budget tracker seeding
# ---------------------------------------------------------------------------


def test_joint_budget_trackers_created_excluding_joint_with_correct_user_id():
    # Arrange
    use_case, bt_repo, _ = make_use_case()

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert all(
        [
            created_names == JOINT_BT_NAMES,
            all(bt.user_id == USER_ID for bt in bt_repo.get_all()),
        ],
    )


def test_created_budget_trackers_are_joint_stamped():
    # Arrange
    use_case, bt_repo, _ = make_use_case()

    # Act
    use_case.execute()

    # Assert
    assert all(
        bt.ownership_type is entities.OwnershipType.JOINT
        and bt.joint_account_id == JOINT_ACCOUNT_ID
        for bt in bt_repo.get_all()
    )


def test_no_budget_trackers_are_duplicated_when_all_already_exist():
    # Arrange
    existing = make_all_joint_trackers()
    use_case, bt_repo, _ = make_use_case(existing_trackers=existing)

    # Act
    use_case.execute()

    # Assert
    assert len(bt_repo.get_all()) == len(JOINT_BT_NAMES)


@pytest.mark.parametrize(
    "missing_name",
    [pytest.param(name, id=name.value) for name in JOINT_BT_NAMES],
)
def test_missing_budget_tracker_is_created_when_others_exist(
    missing_name: entities.BudgetTrackerName,
) -> None:
    # Arrange
    existing = [make_tracker(n) for n in JOINT_BT_NAMES if n != missing_name]
    use_case, bt_repo, _ = make_use_case(existing_trackers=existing)

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert missing_name in created_names


# ---------------------------------------------------------------------------
# Hidden expense source seeding
# ---------------------------------------------------------------------------


def test_hidden_expense_sources_created_for_one_offs_and_savings():
    # Arrange
    use_case, _, es_repo = make_use_case()

    # Act
    use_case.execute()

    # Assert
    created_names = {es.name for es in es_repo.get_all()}
    assert created_names == {name.value for name in JOINT_HIDDEN_BT_NAMES}


def test_created_expense_sources_are_joint_stamped():
    # Arrange
    use_case, _, es_repo = make_use_case()

    # Act
    use_case.execute()

    # Assert
    assert all(
        es.ownership_type is entities.OwnershipType.JOINT
        and es.joint_account_id == JOINT_ACCOUNT_ID
        for es in es_repo.get_all()
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
        for bt_name in JOINT_HIDDEN_BT_NAMES
    )


def test_no_expense_sources_are_duplicated_when_all_already_exist():
    # Arrange
    trackers = make_all_joint_trackers()
    bt_id_by_name = {bt.name: bt.id for bt in trackers}
    existing_sources = [
        entities.ExpenseSourceModel(
            user_id=USER_ID,
            name=bt_name.value,
            budget_tracker_ids=[bt_id_by_name[bt_name]],
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=JOINT_ACCOUNT_ID,
        )
        for bt_name in JOINT_HIDDEN_BT_NAMES
    ]
    use_case, _, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=existing_sources,
    )

    # Act
    use_case.execute()

    # Assert
    assert len(es_repo.get_all()) == len(JOINT_HIDDEN_BT_NAMES)


def test_existing_expense_source_with_none_bt_ids_gets_bt_id_set_and_persisted():
    # Arrange
    trackers = make_all_joint_trackers()
    target_bt_name = entities.BudgetTrackerName.SAVINGS
    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=JOINT_ACCOUNT_ID,
    )
    use_case, bt_repo, es_repo = make_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert - the mutated source is linked and written back
    bt_id = next(bt.id for bt in bt_repo.get_all() if bt.name == target_bt_name)
    assert all(
        [
            bt_id in (existing_source.budget_tracker_ids or []),
            existing_source in es_repo.saved,
        ],
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_no_joint_account_raises_no_joint_account_error():
    # Arrange
    use_case, _, _ = make_use_case(accounts=[])

    # Act / Assert
    with pytest.raises(errors.NoJointAccountToInitialiseError) as exc_info:
        use_case.execute()

    assert exc_info.value.user_id == USER_ID


def test_repository_failure_raises_joint_data_access_error():
    # Arrange
    use_case, bt_repo, _ = make_use_case()
    bt_repo.raise_on_save = True

    # Act
    with pytest.raises(errors.JointDataAccessError) as exc_info:
        use_case.execute()

    # Assert - the user id is in the message and the repository failure is chained
    assert all(
        [
            USER_ID in str(exc_info.value),
            isinstance(exc_info.value.__cause__, port_errors.RepositoryError),
        ],
    )


def test_unexpected_error_is_not_wrapped_as_joint_data_access_error():
    # Arrange - a genuine bug (not a RepositoryError) must propagate untouched.
    use_case, bt_repo, _ = make_use_case()
    boom = ValueError("genuine bug")
    bt_repo.unexpected_error = boom

    # Act / Assert
    with pytest.raises(ValueError, match="genuine bug") as exc_info:
        use_case.execute()

    assert exc_info.value is boom
