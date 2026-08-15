"""Unit tests for the one-offs block's Bank It button."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities, read_models
from use_cases import bank_one_offs

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

_ONE_OFFS_TRACKER_ID = str(uuid.uuid4())


@pytest.fixture(name="build_one_off")
def _build_one_off() -> "Callable[..., read_models.OneOffView]":
    """Return a builder for a one-off view row.

    A test overrides only what it varies — the pledged amount, the budget
    tracker the row hangs off — and inherits the rest.
    """

    def _build(
        current_month: float = 50.0,
        budget_tracker_id: str | None = _ONE_OFFS_TRACKER_ID,
    ) -> read_models.OneOffView:
        return read_models.OneOffView.model_validate(
            {
                "id": uuid.uuid4(),
                "user_id": "auth0|test-user-1",
                "name": "Holiday",
                "cost": 1000.0,
                "current_month": current_month,
                "banked": 0.0,
                "budget_tracker_id": budget_tracker_id,
                "remaining": 1000.0,
                "progress": 0.0,
                "split": 100.0,
                "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            },
        )

    return _build


def _render_wrapper(source, budget_tracker_map, use_case) -> None:  # noqa: ANN001
    """Render the one-offs block for AppTest.

    The arguments are injected via AppTest ``kwargs`` because from_function
    re-runs this body in a fresh namespace where module-level names aren't
    visible.
    """
    from driving_adapters.blocks import one_offs_block

    one_offs_block.render(
        source,
        budget_tracker_map,
        {"bank-account-1": "Current"},
        use_case,
    )


@pytest.fixture(name="build_app_tester")
def _build_app_tester(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_repo: "conftest.RepoBuilder",
) -> "Callable[..., st_test.AppTest]":
    """Return a builder for an AppTest rendering the block over given rows.

    The use case never runs in these render tests, so its repositories stay
    empty fakes.
    """

    def _build(
        rows: "list[read_models.OneOffView] | None" = None,
        budget_tracker_map: dict[str, str] | None = None,
    ) -> st_test.AppTest:
        use_case = bank_one_offs.BankOneOffsUseCase(
            one_off_repo=build_repo(),
            budget_tracker_repo=build_repo(),
            expense_source_repo=build_repo(),
            payment_repo=build_repo(),
        )
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "source": build_stub_data_source(rows or []),
                "budget_tracker_map": budget_tracker_map
                or {_ONE_OFFS_TRACKER_ID: entities.BudgetTrackerName.ONE_OFFS},
                "use_case": use_case,
            },
        )

    return _build


def test_bank_button_renders_with_a_bankable_one_off(
    build_app_tester: "Callable[..., st_test.AppTest]",
    build_one_off: "Callable[..., read_models.OneOffView]",
) -> None:
    # Arrange
    app_tester = build_app_tester([build_one_off()])

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "bank_it_button" for btn in app_tester.button)


def test_bank_button_renders_for_a_row_the_grid_filters_out(
    build_app_tester: "Callable[..., st_test.AppTest]",
    build_one_off: "Callable[..., read_models.OneOffView]",
) -> None:
    # Arrange - the grid narrows itself to the One-offs budget tracker, so a row
    # hanging off no tracker never reaches the display frame. Banking acts on the
    # aggregate, so that must not decide whether the button exists.
    app_tester = build_app_tester([build_one_off(budget_tracker_id=None)])

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "bank_it_button" for btn in app_tester.button)


def test_bank_button_renders_with_nothing_to_bank(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange - an empty ledger is explained inside the dialog rather than by the
    # button silently disappearing.
    app_tester = build_app_tester([])

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "bank_it_button" for btn in app_tester.button)


@pytest.mark.parametrize(
    ("current_month", "expected_count"),
    [(50.0, 1), (0.0, 0)],
)
def test_only_a_pledged_one_off_is_bankable(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_one_off: "Callable[..., read_models.OneOffView]",
    current_month: float,
    expected_count: int,
) -> None:
    # Arrange - banking moves the current month's pledge into Banked, so a
    # one-off pledging nothing this month has nothing to move.
    from driving_adapters.blocks import one_offs_block

    source = build_stub_data_source([build_one_off(current_month=current_month)])

    # Act
    bankable = one_offs_block._bankable_items(source)

    # Assert
    assert len(bankable) == expected_count


def test_bank_button_shares_the_button_row_with_add_and_filter(
    build_app_tester: "Callable[..., st_test.AppTest]",
    build_one_off: "Callable[..., read_models.OneOffView]",
) -> None:
    # Arrange - the three buttons sit in sibling columns of one row rather than
    # stacking, so being present on the page is not enough.
    app_tester = build_app_tester([build_one_off()])

    # Act
    app_tester.run()

    # Assert
    columns = [{btn.key for btn in column.button} for column in app_tester.columns]
    assert all(
        [
            {"one_offs_add_row_button"} in columns,
            {"one_offs_filter_button"} in columns,
            {"bank_it_button"} in columns,
        ],
    )
