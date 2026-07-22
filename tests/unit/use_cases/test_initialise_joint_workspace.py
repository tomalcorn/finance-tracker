"""Tests for InitialiseJointWorkspaceUseCase."""

import uuid
from collections.abc import Callable

import pydantic
import pytest

from domain import entities
from ports import errors as port_errors
from ports import repository
from use_cases import errors
from use_cases.initialise_joint_workspace import InitialiseJointWorkspaceUseCase

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


class FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """In-memory Repository fake for use-case tests.

    Bound to ``pydantic.BaseModel`` rather than ``FinanceTrackerBaseModel``:
    ``JointAccountModel`` carries no user/ownership dimension, so it is not a
    ``FinanceTrackerBaseModel``. ``seed`` pre-loads rows as if already
    persisted, without recording them as saves, so ``saved`` reflects only what
    the use case wrote. The seeding flow only ever reads whole tables and writes
    single rows, so ``get_by_ids`` is unused.
    """

    def __init__(self, items: list[E] | None = None) -> None:
        """Seed the fake with initial items."""
        self._items: list[E] = list(items or [])
        self.saved: list[E] = []

    def seed(self, *items: E) -> None:
        """Pre-load rows as already-persisted (not counted as a save)."""
        self._items.extend(items)

    def get_all(self) -> list[E]:
        return list(self._items)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        raise NotImplementedError

    def save(self, item: E) -> None:
        self._items.append(item)
        self.saved.append(item)

    def apply(self, updates: entities.BackendUpdates) -> None:
        raise NotImplementedError


class FailingRepository[E: pydantic.BaseModel](FakeRepository[E]):
    """Repository fake whose writes always fail at the port boundary."""

    # The item is unused: the stub exists only to fail at the port boundary.
    def save(self, item: E) -> None:  # noqa: ARG002
        msg = "Simulated save failure"
        raise port_errors.RepositoryError(msg)


class BuggyRepository[E: pydantic.BaseModel](FakeRepository[E]):
    """Repository fake whose writes raise an arbitrary (non-port) error."""

    def __init__(self, error: Exception, items: list[E] | None = None) -> None:
        """Store the error the fake raises on every save."""
        super().__init__(items)
        self._error = error

    # The item is unused: the stub exists only to raise the injected bug.
    def save(self, item: E) -> None:  # noqa: ARG002
        raise self._error


BtRepo = FakeRepository[entities.BudgetTrackerItemModel]
EsRepo = FakeRepository[entities.ExpenseSourceModel]
UseCaseBuilder = Callable[..., InitialiseJointWorkspaceUseCase]


@pytest.fixture
def bt_repo() -> BtRepo:
    """Return the budget trackers repository in joint mode."""
    return BtRepo()


@pytest.fixture
def es_repo() -> EsRepo:
    """Return the expense sources repository in joint mode."""
    return EsRepo()


@pytest.fixture
def joint_account() -> entities.JointAccountModel:
    """Return the joint account the workspace is seeded for."""
    return entities.JointAccountModel(id=JOINT_ACCOUNT_ID, name="Ours")


@pytest.fixture
def all_joint_trackers() -> list[entities.BudgetTrackerItemModel]:
    """Return one joint-stamped budget tracker per seeded joint name."""
    return [
        entities.BudgetTrackerItemModel(
            user_id=USER_ID,
            name=name,
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=JOINT_ACCOUNT_ID,
        )
        for name in JOINT_BT_NAMES
    ]


@pytest.fixture
def build_use_case(
    bt_repo: BtRepo,
    es_repo: EsRepo,
    joint_account: entities.JointAccountModel,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A test overrides exactly the collaborator it wants to vary (an empty
    account list, or a repository that fails on write) and inherits the rest,
    including the ``bt_repo``/``es_repo`` fixtures the test seeds and inspects.
    """

    def _build(
        *,
        accounts: list[entities.JointAccountModel] | None = None,
        budget_tracker_repo: BtRepo | None = None,
    ) -> InitialiseJointWorkspaceUseCase:
        return InitialiseJointWorkspaceUseCase(
            user_id=USER_ID,
            budget_tracker_repo=budget_tracker_repo or bt_repo,
            expense_source_repo=es_repo,
            joint_account_repo=FakeRepository(
                [joint_account] if accounts is None else accounts,
            ),
        )

    return _build


@pytest.fixture
def use_case(build_use_case: UseCaseBuilder) -> InitialiseJointWorkspaceUseCase:
    """Return the use case wired to the standard happy-path collaborators."""
    return build_use_case()


# ---------------------------------------------------------------------------
# Budget tracker seeding
# ---------------------------------------------------------------------------


def test_joint_budget_trackers_created_excluding_joint_with_correct_user_id(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert all(
        [
            created_names == JOINT_BT_NAMES,
            all(bt.user_id == USER_ID for bt in bt_repo.get_all()),
        ],
    )


def test_created_budget_trackers_are_joint_stamped(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    assert all(
        bt.ownership_type is entities.OwnershipType.JOINT
        and bt.joint_account_id == JOINT_ACCOUNT_ID
        for bt in bt_repo.get_all()
    )


def test_no_budget_trackers_are_duplicated_when_all_already_exist(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
    all_joint_trackers: list[entities.BudgetTrackerItemModel],
) -> None:
    # Arrange
    bt_repo.seed(*all_joint_trackers)

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
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
    all_joint_trackers: list[entities.BudgetTrackerItemModel],
) -> None:
    # Arrange
    bt_repo.seed(*(t for t in all_joint_trackers if t.name != missing_name))

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert missing_name in created_names


# ---------------------------------------------------------------------------
# Hidden expense source seeding
# ---------------------------------------------------------------------------


def test_hidden_expense_sources_created_for_one_offs_and_savings(
    use_case: InitialiseJointWorkspaceUseCase,
    es_repo: EsRepo,
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    created_names = {es.name for es in es_repo.get_all()}
    assert created_names == {name.value for name in JOINT_HIDDEN_BT_NAMES}


def test_created_expense_sources_are_joint_stamped(
    use_case: InitialiseJointWorkspaceUseCase,
    es_repo: EsRepo,
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    assert all(
        es.ownership_type is entities.OwnershipType.JOINT
        and es.joint_account_id == JOINT_ACCOUNT_ID
        for es in es_repo.get_all()
    )


def test_hidden_expense_source_is_linked_to_its_budget_tracker(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
    es_repo: EsRepo,
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    bt_id_by_name = {bt.name: bt.id for bt in bt_repo.get_all()}
    es_by_name = {es.name: es for es in es_repo.get_all()}
    assert all(
        bt_id_by_name[bt_name] in (es_by_name[bt_name.value].budget_tracker_ids or [])
        for bt_name in JOINT_HIDDEN_BT_NAMES
    )


def test_no_expense_sources_are_duplicated_when_all_already_exist(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
    es_repo: EsRepo,
    all_joint_trackers: list[entities.BudgetTrackerItemModel],
) -> None:
    # Arrange
    bt_repo.seed(*all_joint_trackers)
    bt_id_by_name = {t.name: t.id for t in all_joint_trackers}
    es_repo.seed(
        *(
            entities.ExpenseSourceModel(
                user_id=USER_ID,
                name=bt_name.value,
                budget_tracker_ids=[bt_id_by_name[bt_name]],
                ownership_type=entities.OwnershipType.JOINT,
                joint_account_id=JOINT_ACCOUNT_ID,
            )
            for bt_name in JOINT_HIDDEN_BT_NAMES
        ),
    )

    # Act
    use_case.execute()

    # Assert
    assert len(es_repo.get_all()) == len(JOINT_HIDDEN_BT_NAMES)


def test_existing_expense_source_with_none_bt_ids_gets_bt_id_set_and_persisted(
    use_case: InitialiseJointWorkspaceUseCase,
    bt_repo: BtRepo,
    es_repo: EsRepo,
) -> None:
    # Arrange
    target_bt_name = entities.BudgetTrackerName.SAVINGS
    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=JOINT_ACCOUNT_ID,
    )
    es_repo.seed(existing_source)

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


def test_no_joint_account_raises_no_joint_account_error(
    build_use_case: UseCaseBuilder,
) -> None:
    # Arrange
    use_case = build_use_case(accounts=[])

    # Act / Assert
    with pytest.raises(errors.NoJointAccountToInitialiseError) as exc_info:
        use_case.execute()

    assert exc_info.value.user_id == USER_ID


def test_repository_failure_raises_joint_data_access_error(
    build_use_case: UseCaseBuilder,
) -> None:
    # Arrange
    use_case = build_use_case(budget_tracker_repo=FailingRepository())

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


def test_unexpected_error_is_not_wrapped_as_joint_data_access_error(
    build_use_case: UseCaseBuilder,
) -> None:
    # Arrange - a genuine bug (not a RepositoryError) must propagate untouched.
    boom = ValueError("genuine bug")
    use_case = build_use_case(budget_tracker_repo=BuggyRepository(boom))

    # Act / Assert
    with pytest.raises(ValueError, match="genuine bug") as exc_info:
        use_case.execute()

    assert exc_info.value is boom
