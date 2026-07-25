"""Unit tests for the contribute button."""

from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from driving_adapters.components.buttons import contribute_button
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest


class TestCanSubmit:
    """Tests for the submit-gating logic on the contribute dialog."""

    @pytest.mark.parametrize(
        ("amount", "from_account_id", "to_account_id", "income_source_id", "expected"),
        [
            pytest.param(100.0, "from-1", "to-1", "inc-1", True, id="all_present"),
            pytest.param(None, "from-1", "to-1", "inc-1", False, id="amount_missing"),
            pytest.param(0.0, "from-1", "to-1", "inc-1", False, id="amount_zero"),
            pytest.param(-5.0, "from-1", "to-1", "inc-1", False, id="amount_negative"),
            pytest.param(100.0, None, "to-1", "inc-1", False, id="source_missing"),
            pytest.param(
                100.0,
                "from-1",
                None,
                "inc-1",
                False,
                id="destination_missing",
            ),
            pytest.param(
                100.0,
                "from-1",
                "to-1",
                None,
                False,
                id="income_source_missing",
            ),
        ],
    )
    def test_can_submit(
        self,
        amount: float | None,
        from_account_id: str | None,
        to_account_id: str | None,
        income_source_id: str | None,
        *,
        expected: bool,
    ) -> None:
        # Arrange / Act
        result = contribute_button._can_submit(
            amount,
            from_account_id,
            to_account_id,
            income_source_id,
        )

        # Assert
        assert result is expected


def _button(
    build_repo: "conftest.RepoBuilder",
    joint_bank_account_map: dict[str, str],
    joint_income_source_map: dict[str, str],
) -> contribute_button.ContributeButton:
    """Build a ContributeButton whose use case never runs in the render tests."""
    use_case = ContributeToJointUseCase(
        user_id="auth0|test-user-1",
        personal_payment_repo=build_repo(),
        joint_payment_repo=build_repo(),
        expense_source_repo=build_repo(),
        joint_account_repo=build_repo(),
    )
    return contribute_button.ContributeButton(
        use_case,
        {"personal-1": "Personal Current"},
        joint_bank_account_map,
        joint_income_source_map,
    )


def _dialog_wrapper(button: "contribute_button.ContributeButton") -> None:
    """Render the contribute dialog for AppTest.

    ``button`` is injected via AppTest ``kwargs`` because from_function re-runs
    this body in a fresh namespace where module-level names aren't visible.
    """
    import streamlit as st  # noqa: F401 - needed for app_test from_function

    button._contribute_dialog()


@pytest.fixture(name="build_app_tester")
def _build_app_tester(
    build_repo: "conftest.RepoBuilder",
) -> "Callable[..., st_test.AppTest]":
    """Return a builder for an AppTest rendering the dialog over given maps.

    Both maps default to a populated one, so a test overrides only the dropdown
    whose empty case it is exercising.
    """

    def _build(
        joint_bank_account_map: dict[str, str] | None = None,
        joint_income_source_map: dict[str, str] | None = None,
    ) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _dialog_wrapper,
            default_timeout=120,
            kwargs={
                "button": _button(
                    build_repo,
                    {"joint-1": "Joint Current"}
                    if joint_bank_account_map is None
                    else joint_bank_account_map,
                    {"income-1": "Salary"}
                    if joint_income_source_map is None
                    else joint_income_source_map,
                ),
            },
        )

    return _build


def test_dialog_renders_submit_when_joint_account_exists(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester()

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_submit" for btn in app_tester.button)


def test_dialog_offers_the_joint_income_sources(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester(joint_income_source_map={"income-1": "Salary"})

    # Act
    app_tester.run()

    # Assert - AppTest reports the formatted labels, i.e. what the user picks from.
    assert any(
        box.key == "contribute_income_source" and list(box.options) == ["Salary"]
        for box in app_tester.selectbox
    )


def test_dialog_warns_when_no_joint_bank_account(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester(joint_bank_account_map={})

    # Act
    app_tester.run()

    # Assert
    assert all(
        [
            any(
                "joint bank account" in warning.value for warning in app_tester.warning
            ),
            not any(btn.key == "contribute_submit" for btn in app_tester.button),
        ],
    )


def test_dialog_warns_when_no_joint_income_source(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester(joint_income_source_map={})

    # Act
    app_tester.run()

    # Assert
    assert all(
        [
            any(
                "joint income source" in warning.value for warning in app_tester.warning
            ),
            not any(btn.key == "contribute_submit" for btn in app_tester.button),
        ],
    )
