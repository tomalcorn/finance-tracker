"""Unit tests for the contribute button."""

import uuid

import pydantic
import pytest
import streamlit.testing.v1 as st_test

from domain import entities
from driving_adapters.components.buttons import contribute_button
from ports import repository
from use_cases.contribute_to_joint import ContributeToJointUseCase


class TestValidatedSubmission:
    """Tests for the submit-gating logic on the contribute dialog."""

    @pytest.mark.parametrize(
        ("amount", "from_account_id", "to_account_id", "expected"),
        [
            pytest.param(
                100.0,
                "from-1",
                "to-1",
                (100.0, "from-1", "to-1"),
                id="all_present",
            ),
            pytest.param(None, "from-1", "to-1", None, id="amount_missing"),
            pytest.param(0.0, "from-1", "to-1", None, id="amount_zero"),
            pytest.param(-5.0, "from-1", "to-1", None, id="amount_negative"),
            pytest.param(100.0, None, "to-1", None, id="source_missing"),
            pytest.param(100.0, "from-1", None, None, id="destination_missing"),
        ],
    )
    def test_validated_submission(
        self,
        amount: float | None,
        from_account_id: str | None,
        to_account_id: str | None,
        expected: tuple[float, str, str] | None,
    ) -> None:
        # Arrange / Act
        result = contribute_button._validated_submission(
            amount,
            from_account_id,
            to_account_id,
        )

        # Assert
        assert result == expected


class _FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """No-op Repository fake; the render tests never submit, so nothing runs."""

    def get_all(self) -> list[E]:
        return []

    # ids is unused: the render tests never read by id.
    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:  # noqa: ARG002
        return []

    def save(self, item: E) -> None:
        """No-op; the render tests never write."""

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; the render tests never write."""


def _button(
    joint_bank_account_map: dict[str, str],
) -> contribute_button.ContributeButton:
    """Build a ContributeButton whose use case never runs in the render tests."""
    use_case = ContributeToJointUseCase(
        user_id="auth0|test-user-1",
        personal_payment_repo=_FakeRepository[entities.AnyPaymentModel](),
        joint_payment_repo=_FakeRepository[entities.AnyPaymentModel](),
        expense_source_repo=_FakeRepository[entities.ExpenseSourceModel](),
        joint_account_repo=_FakeRepository[entities.JointAccountModel](),
    )
    return contribute_button.ContributeButton(
        use_case,
        {"personal-1": "Personal Current"},
        joint_bank_account_map,
    )


def _dialog_wrapper(button: "contribute_button.ContributeButton") -> None:
    """Render the contribute dialog for AppTest.

    ``button`` is injected via AppTest ``kwargs`` because from_function re-runs
    this body in a fresh namespace where module-level names aren't visible.
    """
    import streamlit as st  # noqa: F401 - needed for app_test from_function

    button._contribute_dialog()


def _app_tester(joint_bank_account_map: dict[str, str]) -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _dialog_wrapper,
        default_timeout=120,
        kwargs={"button": _button(joint_bank_account_map)},
    )


def test_dialog_renders_submit_when_joint_account_exists() -> None:
    # Arrange
    app_tester = _app_tester({"joint-1": "Joint Current"})

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_submit" for btn in app_tester.button)


def test_dialog_warns_when_no_joint_bank_account() -> None:
    # Arrange
    app_tester = _app_tester({})

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
