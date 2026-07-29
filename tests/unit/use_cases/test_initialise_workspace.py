"""Tests for InitialiseUserWorkspaceUseCase."""

from typing import TYPE_CHECKING

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors, initialise_workspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

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


type BtRepo = conftest.FakeRepository[entities.BudgetTrackerItemModel]
type EsRepo = conftest.FakeRepository[entities.ExpenseSourceModel]
type SettingsRepo = conftest.FakeRepository[entities.UserSettingsModel]
UseCaseBundle = tuple[
    initialise_workspace.InitialiseUserWorkspaceUseCase,
    BtRepo,
    EsRepo,
    SettingsRepo,
]
type UseCaseBuilder = Callable[..., UseCaseBundle]


@pytest.fixture(name="build_use_case")
def _build_use_case(build_repo: "conftest.RepoBuilder") -> "UseCaseBuilder":
    """Return a builder for the use case plus its three repositories.

    A test overrides only what it seeds — existing trackers, sources, settings —
    and inherits empty repositories for the rest. The settings repo is given the
    real parser and personal ownership context so its ``build_entities`` gate
    stamps a saveable default row, as the live repository does.
    """

    def _build(
        existing_trackers: list[entities.BudgetTrackerItemModel] | None = None,
        existing_sources: list[entities.ExpenseSourceModel] | None = None,
        existing_settings: list[entities.UserSettingsModel] | None = None,
    ) -> UseCaseBundle:
        bt_repo = build_repo(existing_trackers)
        es_repo = build_repo(existing_sources)
        settings_repo = build_repo(
            existing_settings,
            parse=entities.UserSettingsModel.model_validate,
            context={"user_id": USER_ID},
        )
        use_case = initialise_workspace.InitialiseUserWorkspaceUseCase(
            user_id=USER_ID,
            budget_tracker_repo=bt_repo,
            expense_source_repo=es_repo,
            settings_repo=settings_repo,
        )
        return use_case, bt_repo, es_repo, settings_repo

    return _build


def make_tracker(name: entities.BudgetTrackerName) -> entities.BudgetTrackerItemModel:
    return entities.BudgetTrackerItemModel(user_id=USER_ID, name=name)


def make_all_trackers() -> list[entities.BudgetTrackerItemModel]:
    return [make_tracker(name) for name in entities.BudgetTrackerName]


# ---------------------------------------------------------------------------
# Budget tracker seeding
# ---------------------------------------------------------------------------


def test_all_budget_tracker_names_are_created_for_a_fresh_user_with_correct_user_id(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    use_case, bt_repo, _, _ = build_use_case()

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


def test_no_budget_trackers_are_duplicated_when_all_already_exist(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    existing = make_all_trackers()
    use_case, bt_repo, _, _ = build_use_case(existing_trackers=existing)

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
    build_use_case: "UseCaseBuilder",
) -> None:
    # Arrange
    existing = [
        make_tracker(n) for n in entities.BudgetTrackerName if n != missing_name
    ]
    use_case, bt_repo, _, _ = build_use_case(existing_trackers=existing)

    # Act
    use_case.execute()

    # Assert
    created_names = {bt.name for bt in bt_repo.get_all()}
    assert missing_name in created_names


# ---------------------------------------------------------------------------
# Hidden expense source seeding
# ---------------------------------------------------------------------------


def test_hidden_expense_sources_created_for_each_hidden_bt_name_with_right_user_id(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    use_case, _, es_repo, _ = build_use_case()

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


def test_hidden_expense_source_is_linked_to_its_budget_tracker(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    use_case, bt_repo, es_repo, _ = build_use_case()

    # Act
    use_case.execute()

    # Assert
    bt_id_by_name = {bt.name: bt.id for bt in bt_repo.get_all()}
    es_by_name = {es.name: es for es in es_repo.get_all()}

    assert all(
        bt_id_by_name[bt_name] in (es_by_name[bt_name.value].budget_tracker_ids or [])
        for bt_name in HIDDEN_BT_NAMES
    )


def test_no_expense_sources_are_duplicated_when_all_already_exist(
    build_use_case: "UseCaseBuilder",
):
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
    use_case, _, es_repo, _ = build_use_case(
        existing_trackers=trackers,
        existing_sources=existing_sources,
    )

    # Act
    use_case.execute()

    # Assert
    assert len(es_repo.get_all()) == len(HIDDEN_BT_NAMES)


def test_existing_expense_source_with_missing_bt_id_gets_it_added(
    build_use_case: "UseCaseBuilder",
):
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
    use_case, _, es_repo, _ = build_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert
    updated = es_repo.get_by_id(existing_source.id)
    assert updated is not None
    assert bt_id_by_name[target_bt_name] in (updated.budget_tracker_ids or [])


def test_existing_expense_source_with_none_bt_ids_gets_bt_id_set(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    trackers = make_all_trackers()
    target_bt_name = entities.BudgetTrackerName.SAVINGS

    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
    )
    use_case, bt_repo, es_repo, _ = build_use_case(
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


def test_existing_expense_source_with_none_bt_ids_is_persisted(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    trackers = make_all_trackers()
    target_bt_name = entities.BudgetTrackerName.SAVINGS
    existing_source = entities.ExpenseSourceModel(
        user_id=USER_ID,
        name=target_bt_name.value,
        budget_tracker_ids=None,
    )
    use_case, _, es_repo, _ = build_use_case(
        existing_trackers=trackers,
        existing_sources=[existing_source],
    )

    # Act
    use_case.execute()

    # Assert - a linked copy of the source is written back, not just changed in
    # memory (entities are frozen, so the stored row is a new object)
    assert existing_source.id in [saved.id for saved in es_repo.saved]


# ---------------------------------------------------------------------------
# Settings seeding
# ---------------------------------------------------------------------------


def make_settings(
    period: entities.IncomeRollUpPeriod,
) -> entities.UserSettingsModel:
    return entities.UserSettingsModel(user_id=USER_ID, income_roll_up_period=period)


def test_default_settings_row_created_for_a_fresh_user(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    use_case, _, _, settings_repo = build_use_case()

    # Act
    use_case.execute()

    # Assert
    rows = settings_repo.get_all()
    assert all(
        [
            len(rows) == 1,
            rows[0].user_id == USER_ID,
            rows[0].income_roll_up_period is entities.IncomeRollUpPeriod.CURRENT_MONTH,
        ],
    )


def test_no_settings_row_created_when_one_already_exists(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    existing = make_settings(entities.IncomeRollUpPeriod.CURRENT_MONTH)
    use_case, _, _, settings_repo = build_use_case(existing_settings=[existing])

    # Act
    use_case.execute()

    # Assert - the write list is empty and the single row is untouched
    assert all([settings_repo.saved == [], len(settings_repo.get_all()) == 1])


def test_existing_non_default_settings_row_is_not_overwritten(
    build_use_case: "UseCaseBuilder",
):
    # Arrange - a row carrying a non-default period must survive create-if-missing
    existing = make_settings(entities.IncomeRollUpPeriod.PREVIOUS_MONTH)
    use_case, _, _, settings_repo = build_use_case(existing_settings=[existing])

    # Act
    use_case.execute()

    # Assert
    rows = settings_repo.get_all()
    assert all(
        [
            settings_repo.saved == [],
            rows[0].income_roll_up_period is entities.IncomeRollUpPeriod.PREVIOUS_MONTH,
        ],
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_repository_failure_raises_data_access_error(
    build_use_case: "UseCaseBuilder",
):
    # Arrange
    use_case, bt_repo, _, _ = build_use_case()
    bt_repo.save_error = port_errors.RepositoryError("backend unavailable")

    # Act
    with pytest.raises(errors.DataAccessError) as exc_info:
        use_case.execute()

    # Assert - the user id is in the message and the repository failure is chained
    assert all(
        [
            USER_ID in str(exc_info.value),
            isinstance(exc_info.value.__cause__, port_errors.RepositoryError),
        ],
    )


def test_unexpected_error_is_not_wrapped_as_data_access_error(
    build_use_case: "UseCaseBuilder",
):
    # Arrange - a genuine bug (not a RepositoryError) must propagate untouched
    # rather than being masked as a workspace-init failure.
    use_case, bt_repo, _, _ = build_use_case()
    boom = ValueError("genuine bug")
    bt_repo.save_error = boom

    # Act / Assert
    with pytest.raises(ValueError, match="genuine bug") as exc_info:
        use_case.execute()

    assert exc_info.value is boom
