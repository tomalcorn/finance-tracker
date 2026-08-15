"""Unit tests for the one-offs block's Bank It button."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

import pytest
import streamlit.testing.v1 as st_test

from domain import entities, read_models
from use_cases import bank_one_offs

if TYPE_CHECKING:
    from collections.abc import Callable

_ONE_OFFS_ROOT_ID = str(uuid.uuid4())


@pytest.fixture(name="build_category")
def _build_category() -> "Callable[..., read_models.CategoryView]":
    """Return a builder for a category view row, a pot unless told otherwise.

    A test overrides only what it varies — the planned spend, the accrual window
    that tells a pot from a monthly category — and inherits the rest.
    """

    def _build(
        budget: float = 50.0,
        accrual: entities.AccrualPeriod = entities.AccrualPeriod.MULTI_MONTH,
        parent_id: str | None = _ONE_OFFS_ROOT_ID,
    ) -> read_models.CategoryView:
        return read_models.CategoryView.model_validate(
            {
                "id": uuid.uuid4(),
                "user_id": "auth0|test-user-1",
                "name": "Holiday",
                "parent_id": parent_id,
                "budget": budget,
                "accrual": accrual,
                "cost": 1000.0,
                "starting_balance": 0.0,
                "current_month": 0.0,
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
    build_stub_data_source: "Callable[..., Any]",
    build_repo: "Callable[..., Any]",
) -> "Callable[..., st_test.AppTest]":
    """Return a builder for an AppTest rendering the block over given rows.

    The use case never runs in these render tests, so its repositories stay
    empty fakes.
    """

    def _build(
        rows: "list[read_models.CategoryView] | None" = None,
        budget_tracker_map: dict[str, str] | None = None,
    ) -> st_test.AppTest:
        use_case = bank_one_offs.BankOneOffsUseCase(
            category_repo=build_repo(),
            payment_repo=build_repo(),
        )
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "source": build_stub_data_source(rows or []),
                "budget_tracker_map": budget_tracker_map
                or {_ONE_OFFS_ROOT_ID: entities.BudgetTrackerName.ONE_OFFS},
                "use_case": use_case,
            },
        )

    return _build


def test_bank_button_renders_with_a_bankable_pot(
    build_app_tester: "Callable[..., st_test.AppTest]",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange
    app_tester = build_app_tester([build_category()])

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
    ("budget", "expected_count"),
    [(50.0, 1), (0.0, 0)],
)
def test_only_a_pot_with_a_planned_spend_is_bankable(
    build_stub_data_source: "Callable[..., Any]",
    build_category: "Callable[..., read_models.CategoryView]",
    budget: float,
    expected_count: int,
) -> None:
    # Arrange - banking pays this month's planned spend into the pot, so a pot
    # planning nothing this month has nothing to pay in.
    from driving_adapters.blocks import one_offs_block

    source = build_stub_data_source([build_category(budget=budget)])

    # Act
    bankable = one_offs_block._bankable_items(source)

    # Assert
    assert len(bankable) == expected_count


def test_a_monthly_category_is_never_bankable(
    build_stub_data_source: "Callable[..., Any]",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - the one source serves every category grid, so the block's own
    # slice is what keeps an ordinary expense category out of the dialog.
    from driving_adapters.blocks import one_offs_block

    source = build_stub_data_source(
        [build_category(accrual=entities.AccrualPeriod.MONTHLY)],
    )

    # Act
    bankable = one_offs_block._bankable_items(source)

    # Assert
    assert bankable == []


def test_bank_button_shares_the_button_row_with_add_and_filter(
    build_app_tester: "Callable[..., st_test.AppTest]",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - the three buttons sit in sibling columns of one row rather than
    # stacking, so being present on the page is not enough.
    app_tester = build_app_tester([build_category()])

    # Act
    app_tester.run()

    # Assert
    columns = [{btn.key for btn in column.button} for column in app_tester.columns]
    assert all(
        [
            {"one_off_categories_add_row_button"} in columns,
            {"one_off_categories_filter_button"} in columns,
            {"bank_it_button"} in columns,
        ],
    )
