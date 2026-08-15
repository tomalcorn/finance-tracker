"""Tests for InitialiseUserWorkspaceUseCase."""

import uuid
from typing import TYPE_CHECKING, Any

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors, initialise_workspace

if TYPE_CHECKING:
    from collections.abc import Callable

USER_ID = "user-abc"
ALL_ROOT_NAMES = set(entities.BudgetTrackerName)


@pytest.fixture(name="category_repo")
def _category_repo(build_repo: "Callable[..., Any]") -> Any:  # noqa: ANN401
    """Return the categories fake the seed reads and writes."""
    return build_repo()


@pytest.fixture(name="settings_repo")
def _settings_repo(build_repo: "Callable[..., Any]") -> Any:  # noqa: ANN401
    """Return the settings fake, gated the way the live repository is.

    It is given the real parser and personal ownership context so its
    ``build_entities`` gate stamps a saveable default row.
    """
    return build_repo(
        parse=entities.UserSettingsModel.model_validate,
        context={"user_id": USER_ID},
    )


@pytest.fixture(name="use_case")
def _use_case(
    category_repo: Any,  # noqa: ANN401
    settings_repo: Any,  # noqa: ANN401
) -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Return the use case wired to the two fakes."""
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=USER_ID,
        category_repo=category_repo,
        settings_repo=settings_repo,
    )


@pytest.fixture(name="build_root")
def _build_root() -> "Callable[..., entities.CategoryModel]":
    """Return a builder for a seeded root category."""

    def _build(name: entities.BudgetTrackerName) -> entities.CategoryModel:
        return entities.CategoryModel(user_id=USER_ID, name=name)

    return _build


def test_all_root_categories_are_created_for_a_fresh_user_with_correct_user_id(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
):
    # Arrange - a fresh user has no categories at all

    # Act
    use_case.execute()

    # Assert
    created = category_repo.get_all()
    assert all(
        [
            {category.name for category in created} == set(ALL_ROOT_NAMES),
            all(category.user_id == USER_ID for category in created),
        ],
    )


def test_seeded_categories_are_roots(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
):
    """Only roots are seeded: everything below them is the user's own (#250)."""
    # Arrange - a fresh user has no categories at all

    # Act
    use_case.execute()

    # Assert
    assert all(category.is_root for category in category_repo.get_all())


def test_no_root_categories_are_duplicated_when_all_already_exist(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
    build_root: "Callable[..., entities.CategoryModel]",
):
    # Arrange
    category_repo.seed(*[build_root(name) for name in entities.BudgetTrackerName])

    # Act
    use_case.execute()

    # Assert
    assert len(category_repo.get_all()) == len(ALL_ROOT_NAMES)


@pytest.mark.parametrize(
    "missing_name",
    [pytest.param(name, id=name.value) for name in entities.BudgetTrackerName],
)
def test_missing_root_category_is_created_when_others_exist(
    missing_name: entities.BudgetTrackerName,
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
    build_root: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange
    category_repo.seed(
        *[
            build_root(name)
            for name in entities.BudgetTrackerName
            if name != missing_name
        ],
    )

    # Act
    use_case.execute()

    # Assert
    assert missing_name in {category.name for category in category_repo.get_all()}


def test_a_child_sharing_a_root_name_does_not_stand_in_for_the_root(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
):
    """A user's own "Savings" under Expenses is not the Savings root."""
    # Arrange
    category_repo.seed(
        entities.CategoryModel(
            user_id=USER_ID,
            name=entities.BudgetTrackerName.SAVINGS.value,
            parent_id=uuid.uuid4(),
        ),
    )

    # Act
    use_case.execute()

    # Assert
    seeded_roots = {
        category.name for category in category_repo.get_all() if category.is_root
    }
    assert seeded_roots == set(ALL_ROOT_NAMES)


def test_default_settings_row_created_for_a_fresh_user(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
):
    # Arrange - a fresh user has no settings row

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
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
):
    # Arrange
    settings_repo.seed(
        entities.UserSettingsModel(
            user_id=USER_ID,
            income_roll_up_period=entities.IncomeRollUpPeriod.CURRENT_MONTH,
        ),
    )

    # Act
    use_case.execute()

    # Assert - the write list is empty and the single row is untouched
    assert all([settings_repo.saved == [], len(settings_repo.get_all()) == 1])


def test_existing_non_default_settings_row_is_not_overwritten(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
):
    # Arrange - a row carrying a non-default period must survive create-if-missing
    settings_repo.seed(
        entities.UserSettingsModel(
            user_id=USER_ID,
            income_roll_up_period=entities.IncomeRollUpPeriod.PREVIOUS_MONTH,
        ),
    )

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


def test_repository_failure_raises_data_access_error(
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
):
    # Arrange
    category_repo.save_error = port_errors.RepositoryError("backend unavailable")

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
    use_case: initialise_workspace.InitialiseUserWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
):
    # Arrange - a genuine bug (not a RepositoryError) must propagate untouched
    # rather than being masked as a workspace-init failure.
    boom = ValueError("genuine bug")
    category_repo.save_error = boom

    # Act / Assert
    with pytest.raises(ValueError, match="genuine bug") as exc_info:
        use_case.execute()

    assert exc_info.value is boom
