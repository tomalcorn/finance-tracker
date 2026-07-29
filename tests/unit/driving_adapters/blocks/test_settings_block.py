"""Unit tests for the settings block."""

from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities
from use_cases.manage_user_settings import ManageUserSettingsUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

USER_ID = "auth0|test-user-1"

_CURRENT = entities.IncomeRollUpPeriod.CURRENT_MONTH
_PREVIOUS = entities.IncomeRollUpPeriod.PREVIOUS_MONTH

type SettingsRepo = conftest.FakeRepository[entities.UserSettingsModel]
type AppTesterBuilder = Callable[..., tuple[st_test.AppTest, SettingsRepo]]


def _render_wrapper(
    use_case: "ManageUserSettingsUseCase",
    ownership: "entities.OwnershipType",
) -> None:
    """Render the settings block for AppTest.

    Injected via AppTest ``kwargs`` because from_function re-runs this body in a
    fresh namespace where module-level names aren't visible.
    """
    from driving_adapters.blocks import settings_block

    settings_block.render(use_case, ownership)


@pytest.fixture(name="build_app_tester")
def _build_app_tester(
    build_repo: "conftest.RepoBuilder",
) -> "AppTesterBuilder":
    """Return a builder for an AppTest rendering the block over a fake repo."""

    def _build(
        stored: entities.UserSettingsModel | None = None,
        ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
    ) -> "tuple[st_test.AppTest, SettingsRepo]":
        repo = build_repo(
            [stored] if stored else [],
            parse=entities.UserSettingsModel.model_validate,
            context={"user_id": USER_ID},
        )
        app_tester = st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "use_case": ManageUserSettingsUseCase(settings_repo=repo),
                "ownership": ownership,
            },
        )
        # The repository comes back alongside the tester so a test can assert on
        # what the block wrote, not merely on what it rendered.
        return app_tester, repo

    return _build


def test_the_selectbox_opens_on_the_stored_period(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange
    stored = entities.UserSettingsModel(
        user_id=USER_ID,
        income_roll_up_period=_PREVIOUS,
    )
    app_tester, _ = build_app_tester(stored)

    # Act
    app_tester.run()

    # Assert
    assert app_tester.selectbox[0].value is _PREVIOUS


def test_the_stored_period_is_not_rewritten_on_load(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange
    app_tester, repo = build_app_tester()

    # Act
    app_tester.run()

    # Assert - merely rendering the block writes nothing.
    assert repo.saved == []


def test_changing_the_period_writes_it(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange
    app_tester, repo = build_app_tester()
    app_tester.run()

    # Act - no Save button; changing the selection is the write.
    app_tester.selectbox[0].set_value(_PREVIOUS).run()

    # Assert
    assert [row.income_roll_up_period for row in repo.saved] == [_PREVIOUS]


def test_the_two_halves_do_not_share_widget_state(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange - the settings page renders this block twice on one page, so a
    # shared widget key would make the joint control echo the personal one.
    personal, _ = build_app_tester(ownership=entities.OwnershipType.PERSONAL)
    joint, _ = build_app_tester(ownership=entities.OwnershipType.JOINT)

    # Act
    personal.run()
    joint.run()

    # Assert
    assert personal.selectbox[0].key != joint.selectbox[0].key


def test_a_failed_save_is_reported_rather_than_raised(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange
    from ports import errors as port_errors

    app_tester, repo = build_app_tester()
    app_tester.run()
    repo.save_error = port_errors.RepositoryError("boom")

    # Act
    app_tester.selectbox[0].set_value(_PREVIOUS).run()

    # Assert
    assert not app_tester.exception
    assert app_tester.error


def test_reselecting_the_stored_period_writes_nothing(
    build_app_tester: "AppTesterBuilder",
) -> None:
    # Arrange - selecting the value that is already stored is a no-op the write
    # path must never reach.
    stored = entities.UserSettingsModel(
        user_id=USER_ID,
        income_roll_up_period=_CURRENT,
    )
    app_tester, repo = build_app_tester(stored)
    app_tester.run()

    # Act
    app_tester.selectbox[0].set_value(_CURRENT).run()

    # Assert
    assert repo.saved == []
