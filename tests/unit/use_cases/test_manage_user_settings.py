"""Tests for ManageUserSettingsUseCase."""

import uuid
from typing import TYPE_CHECKING

import pytest

from domain import entities
from ports import errors as port_errors
from use_cases import errors
from use_cases.manage_user_settings import ManageUserSettingsUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

USER_ID = "user-123"
JOINT_ACCOUNT_ID = uuid.uuid4()

type SettingsRepo = conftest.FakeRepository[entities.UserSettingsModel]

_CURRENT = entities.IncomeRollUpPeriod.CURRENT_MONTH
_PREVIOUS = entities.IncomeRollUpPeriod.PREVIOUS_MONTH


@pytest.fixture(name="build_settings_repo")
def _build_settings_repo(
    build_repo: "conftest.RepoBuilder",
) -> "Callable[..., SettingsRepo]":
    """Return a builder for a settings repository fake.

    The context mirrors the real repository's write gate: a raw row arrives
    without the fields that decide whose settings these are, and the gate fills
    them in before validating.
    """

    def _build(
        stored: "list[entities.UserSettingsModel] | None" = None,
        context: "entities.RawRow | None" = None,
    ) -> "SettingsRepo":
        return build_repo(
            stored or [],
            parse=entities.UserSettingsModel.model_validate,
            context=context or {"user_id": USER_ID},
        )

    return _build


def test_load_defaults_when_nothing_is_stored(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange - a user who has never changed a setting has no row at all.
    repo = build_settings_repo()
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act
    settings = use_case.load()

    # Assert
    assert settings.income_roll_up_period is _CURRENT
    assert repo.saved == []


def test_load_default_is_stamped_by_the_repositorys_gate(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange - the default must arrive owned the way this repository writes, so
    # the first change to it is a saveable row rather than an ownerless one.
    context = {
        "user_id": USER_ID,
        "ownership_type": entities.OwnershipType.JOINT,
        "joint_account_id": str(JOINT_ACCOUNT_ID),
    }
    use_case = ManageUserSettingsUseCase(
        settings_repo=build_settings_repo(context=context),
    )

    # Act
    settings = use_case.load()

    # Assert
    assert settings.ownership_type is entities.OwnershipType.JOINT
    assert settings.joint_account_id == JOINT_ACCOUNT_ID


def test_load_returns_the_stored_settings(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange
    stored = entities.UserSettingsModel(
        user_id=USER_ID,
        income_roll_up_period=_PREVIOUS,
    )
    use_case = ManageUserSettingsUseCase(
        settings_repo=build_settings_repo([stored]),
    )

    # Act
    settings = use_case.load()

    # Assert
    assert settings == stored


def test_setting_the_period_writes_the_row(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange
    repo = build_settings_repo()
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act
    updated = use_case.set_income_roll_up_period(_PREVIOUS)

    # Assert
    assert updated.income_roll_up_period is _PREVIOUS
    assert [saved.income_roll_up_period for saved in repo.saved] == [_PREVIOUS]


def test_setting_the_period_keeps_the_stored_rows_identity(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange - a change updates the existing row rather than adding a rival one
    # the unique index would reject.
    stored = entities.UserSettingsModel(user_id=USER_ID)
    repo = build_settings_repo([stored])
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act
    use_case.set_income_roll_up_period(_PREVIOUS)

    # Assert
    assert [saved.id for saved in repo.saved] == [stored.id]


def test_setting_the_period_it_already_has_writes_nothing(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange - a no-op write would still bust the income and budget-tracker
    # cache entries, costing a refetch for a change that never happened.
    stored = entities.UserSettingsModel(
        user_id=USER_ID,
        income_roll_up_period=_PREVIOUS,
    )
    repo = build_settings_repo([stored])
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act
    use_case.set_income_roll_up_period(_PREVIOUS)

    # Assert
    assert repo.saved == []


def test_a_failed_read_is_reported_as_a_settings_read_error(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange
    repo = build_settings_repo()
    repo.read_error = port_errors.RepositoryError("boom")
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act / Assert
    with pytest.raises(errors.UserSettingsReadError):
        use_case.load()


def test_a_failed_write_is_reported_as_a_settings_write_error(
    build_settings_repo: "Callable[..., SettingsRepo]",
) -> None:
    # Arrange
    repo = build_settings_repo()
    repo.save_error = port_errors.RepositoryError("boom")
    use_case = ManageUserSettingsUseCase(settings_repo=repo)

    # Act / Assert
    with pytest.raises(errors.UserSettingsWriteError):
        use_case.set_income_roll_up_period(_PREVIOUS)
