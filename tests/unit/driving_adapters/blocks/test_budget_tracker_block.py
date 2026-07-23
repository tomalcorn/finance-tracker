"""Unit tests for the budget tracker block's contribute-button wiring."""

import uuid
from typing import TYPE_CHECKING

import pydantic
import streamlit.testing.v1 as st_test

from domain import entities
from driving_adapters.components.buttons import contribute_button
from ports import repository
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from driving_adapters.components.dfes import data_source as data_source_mod


class _StubDataSource:
    """GridDataSource stub: empty reads so the block falls back to sample data."""

    def rows(self) -> list[pydantic.BaseModel]:
        return []

    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return set()

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; the render tests never write."""


class _FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """No-op Repository fake; the render tests never drive the use case."""

    def get_all(self) -> list[E]:
        return []

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:  # noqa: ARG002
        return []

    def save(self, item: E) -> None:
        """No-op; the render tests never write."""

    def apply(self, updates: entities.BackendUpdates) -> None:
        """No-op; the render tests never write."""


def _contribute_button() -> contribute_button.ContributeButton:
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
        {"joint-1": "Joint Current"},
    )


def _render_wrapper(
    button: "contribute_button.ContributeButton | None",
    source: "data_source_mod.GridDataSource",
) -> None:
    """Render the budget tracker block for AppTest.

    ``button`` and ``source`` are injected via AppTest ``kwargs`` because
    from_function re-runs this body in a fresh namespace where module-level
    names aren't visible.
    """
    from driving_adapters.blocks import budget_tracker_block

    budget_tracker_block.render(source, source, source, {}, button)


def _app_tester(button: "contribute_button.ContributeButton | None") -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _render_wrapper,
        default_timeout=120,
        kwargs={"button": button, "source": _StubDataSource()},
    )


def test_render_shows_contribute_button_when_provided() -> None:
    # Arrange
    app_tester = _app_tester(_contribute_button())

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_button" for btn in app_tester.button)


def test_render_omits_contribute_button_when_absent() -> None:
    # Arrange
    app_tester = _app_tester(None)

    # Act
    app_tester.run()

    # Assert
    assert not any(btn.key == "contribute_button" for btn in app_tester.button)
