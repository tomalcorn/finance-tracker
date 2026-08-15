"""Tests for InitialiseJointWorkspaceUseCase."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors
from use_cases.initialise_joint_workspace import InitialiseJointWorkspaceUseCase

USER_ID = "user-abc"
JOINT_ACCOUNT_ID = uuid.uuid4()

# The joint seed creates every root category except JOINT.
JOINT_ROOT_NAMES = {
    name
    for name in entities.BudgetTrackerName
    if name is not entities.BudgetTrackerName.JOINT
}

UseCaseBuilder = Callable[..., InitialiseJointWorkspaceUseCase]


@pytest.fixture
def category_repo(build_repo: "Callable[..., Any]") -> Any:  # noqa: ANN401
    """Return the categories repository in joint mode."""
    return build_repo()


@pytest.fixture
def settings_repo(build_repo: "Callable[..., Any]") -> Any:  # noqa: ANN401
    """Return the settings repository in joint mode.

    Given the real parser and joint ownership context so its ``build_entities``
    gate stamps the account id on the default row, as the live joint repository
    resolves and stamps it itself.
    """
    return build_repo(
        parse=entities.UserSettingsModel.model_validate,
        context={
            "user_id": USER_ID,
            "ownership_type": entities.OwnershipType.JOINT,
            "joint_account_id": JOINT_ACCOUNT_ID,
        },
    )


@pytest.fixture
def joint_account() -> entities.JointAccountModel:
    """Return the joint account the workspace is seeded for."""
    return entities.JointAccountModel(id=JOINT_ACCOUNT_ID, name="Ours")


@pytest.fixture
def all_joint_roots() -> list[entities.CategoryModel]:
    """Return one joint-stamped root category per seeded joint name."""
    return [
        entities.CategoryModel(
            user_id=USER_ID,
            name=name,
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=JOINT_ACCOUNT_ID,
        )
        for name in JOINT_ROOT_NAMES
    ]


@pytest.fixture
def build_use_case(
    build_repo: "Callable[..., Any]",
    category_repo: Any,  # noqa: ANN401
    settings_repo: Any,  # noqa: ANN401
    joint_account: entities.JointAccountModel,
) -> UseCaseBuilder:
    """Return a builder for the use case wired to the standard collaborators.

    A test overrides exactly the collaborator it wants to vary (an empty
    account list, or a repository that fails on write) and inherits the rest,
    including the ``category_repo``/``settings_repo`` fixtures the test seeds
    and inspects.
    """

    def _build(
        *,
        accounts: list[entities.JointAccountModel] | None = None,
        categories_repo: Any = None,  # noqa: ANN401
    ) -> InitialiseJointWorkspaceUseCase:
        return InitialiseJointWorkspaceUseCase(
            user_id=USER_ID,
            category_repo=categories_repo or category_repo,
            joint_account_repo=build_repo(
                [joint_account] if accounts is None else accounts,
            ),
            settings_repo=settings_repo,
        )

    return _build


@pytest.fixture
def use_case(build_use_case: UseCaseBuilder) -> InitialiseJointWorkspaceUseCase:
    """Return the use case wired to the standard happy-path collaborators."""
    return build_use_case()


def test_joint_root_categories_created_excluding_joint_with_correct_user_id(
    use_case: InitialiseJointWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    created = category_repo.get_all()
    assert all(
        [
            {category.name for category in created} == JOINT_ROOT_NAMES,
            all(category.user_id == USER_ID for category in created),
        ],
    )


def test_created_categories_are_joint_stamped_roots(
    use_case: InitialiseJointWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    assert all(
        category.is_root
        and category.ownership_type is entities.OwnershipType.JOINT
        and category.joint_account_id == JOINT_ACCOUNT_ID
        for category in category_repo.get_all()
    )


def test_no_root_categories_are_duplicated_when_all_already_exist(
    use_case: InitialiseJointWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
    all_joint_roots: list[entities.CategoryModel],
) -> None:
    # Arrange
    category_repo.seed(*all_joint_roots)

    # Act
    use_case.execute()

    # Assert
    assert len(category_repo.get_all()) == len(JOINT_ROOT_NAMES)


@pytest.mark.parametrize(
    "missing_name",
    [pytest.param(name, id=name.value) for name in JOINT_ROOT_NAMES],
)
def test_missing_root_category_is_created_when_others_exist(
    missing_name: entities.BudgetTrackerName,
    use_case: InitialiseJointWorkspaceUseCase,
    category_repo: Any,  # noqa: ANN401
    all_joint_roots: list[entities.CategoryModel],
) -> None:
    # Arrange
    category_repo.seed(*(r for r in all_joint_roots if r.name != missing_name))

    # Act
    use_case.execute()

    # Assert
    assert missing_name in {category.name for category in category_repo.get_all()}


def test_default_settings_row_created_for_the_account(
    use_case: InitialiseJointWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    rows = settings_repo.get_all()
    assert all(
        [
            len(rows) == 1,
            rows[0].income_roll_up_period is entities.IncomeRollUpPeriod.CURRENT_MONTH,
        ],
    )


def test_created_settings_row_is_joint_stamped(
    use_case: InitialiseJointWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange / Act
    use_case.execute()

    # Assert
    row = settings_repo.get_all()[0]
    assert all(
        [
            row.ownership_type is entities.OwnershipType.JOINT,
            row.joint_account_id == JOINT_ACCOUNT_ID,
        ],
    )


def test_no_settings_row_created_when_one_already_exists(
    use_case: InitialiseJointWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange
    settings_repo.seed(
        entities.UserSettingsModel(
            user_id=USER_ID,
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=JOINT_ACCOUNT_ID,
        ),
    )

    # Act
    use_case.execute()

    # Assert - the write list is empty and the single row is untouched
    assert all([settings_repo.saved == [], len(settings_repo.get_all()) == 1])


def test_existing_non_default_settings_row_is_not_overwritten(
    use_case: InitialiseJointWorkspaceUseCase,
    settings_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange - a row carrying a non-default period must survive create-if-missing
    settings_repo.seed(
        entities.UserSettingsModel(
            user_id=USER_ID,
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=JOINT_ACCOUNT_ID,
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


def test_no_joint_account_seeds_nothing(
    build_use_case: UseCaseBuilder,
    category_repo: Any,  # noqa: ANN401
    settings_repo: Any,  # noqa: ANN401
) -> None:
    # Arrange - a user in no joint account has nothing to seed, so this is a
    # no-op rather than a failure: the entry point runs it for every user.
    use_case = build_use_case(accounts=[])

    # Act
    use_case.execute()

    # Assert
    assert all([category_repo.saved == [], settings_repo.saved == []])


def test_repository_failure_raises_joint_data_access_error(
    build_use_case: UseCaseBuilder,
    build_repo: "Callable[..., Any]",
) -> None:
    # Arrange
    failing = build_repo()
    failing.save_error = port_errors.RepositoryError("Simulated save failure")
    use_case = build_use_case(categories_repo=failing)

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
    build_repo: "Callable[..., Any]",
) -> None:
    # Arrange - a genuine bug (not a RepositoryError) must propagate untouched.
    boom = ValueError("genuine bug")
    buggy = build_repo()
    buggy.save_error = boom
    use_case = build_use_case(categories_repo=buggy)

    # Act / Assert
    with pytest.raises(ValueError, match="genuine bug") as exc_info:
        use_case.execute()

    assert exc_info.value is boom
