"""Unit tests for the budget tracker block's contribute button and income tab."""

from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities
from driving_adapters.components.buttons import contribute_button
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

    from driving_adapters.components.dfes import data_source as data_source_mod


@pytest.fixture(name="contribute_btn")
def _contribute_btn(
    build_repo: "conftest.RepoBuilder",
) -> contribute_button.ContributeButton:
    """Return a ContributeButton whose use case never runs in the render tests."""
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
        {"joint-1": "Joint Current"},
        {"income-1": "Salary"},
    )


def _render_wrapper(
    button: "contribute_button.ContributeButton | None",
    source: "data_source_mod.GridDataSource",
    period: "entities.IncomeRollUpPeriod",
) -> None:
    """Render the budget tracker block for AppTest.

    The arguments are injected via AppTest ``kwargs`` because from_function
    re-runs this body in a fresh namespace where module-level names aren't
    visible. One stub source stands in for all three tabs.
    """
    from driving_adapters.blocks import budget_tracker_block

    sources = budget_tracker_block.BudgetTrackerSources(source, source, source)
    budget_tracker_block.render(sources, {}, button, period)


@pytest.fixture(name="build_app_tester")
def _build_app_tester(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> "Callable[..., st_test.AppTest]":
    """Return a builder for an AppTest rendering the block, button or not."""

    def _build(
        button: contribute_button.ContributeButton | None,
        period: entities.IncomeRollUpPeriod = (
            entities.IncomeRollUpPeriod.CURRENT_MONTH
        ),
    ) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "button": button,
                "source": build_stub_data_source(),
                "period": period,
            },
        )

    return _build


def test_render_shows_contribute_button_when_provided(
    build_app_tester: "Callable[..., st_test.AppTest]",
    contribute_btn: contribute_button.ContributeButton,
) -> None:
    # Arrange
    app_tester = build_app_tester(contribute_btn)

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_button" for btn in app_tester.button)


def test_contribute_button_shares_the_button_row_with_filter(
    build_app_tester: "Callable[..., st_test.AppTest]",
    contribute_btn: contribute_button.ContributeButton,
) -> None:
    # Arrange - the contribute button sits *alongside* the grid's filter button
    # rather than stacking above it, so the two must land in sibling columns of
    # one row, not merely both be present on the page.
    app_tester = build_app_tester(contribute_btn)

    # Act
    app_tester.run()

    # Assert
    columns = [{btn.key for btn in column.button} for column in app_tester.columns]
    assert all(
        [
            {"budget_tracker_filter_button"} in columns,
            {"contribute_button"} in columns,
        ],
    )


def test_render_omits_contribute_button_when_absent(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester(None)

    # Act
    app_tester.run()

    # Assert
    assert not any(btn.key == "contribute_button" for btn in app_tester.button)


@pytest.mark.parametrize(
    ("period", "expected_label"),
    [
        (entities.IncomeRollUpPeriod.CURRENT_MONTH, "Current Month"),
        (entities.IncomeRollUpPeriod.PREVIOUS_MONTH, "Previous Month"),
    ],
)
def test_income_roll_up_column_is_labelled_for_the_configured_month(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    period: entities.IncomeRollUpPeriod,
    expected_label: str,
) -> None:
    # Arrange - the column is always `current_month`; the view moves its window,
    # so only the heading says which month is being shown.
    from driving_adapters.blocks import budget_tracker_block

    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source, source)

    # Act
    _, _, income_config = budget_tracker_block._configs(sources, {}, period)

    # Assert
    roll_up_column = next(
        column
        for column in income_config.display.columns
        if column.column_name == "current_month"
    )
    assert roll_up_column.column_config["label"] == expected_label


def test_income_tab_explains_a_moved_roll_up_window(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange
    app_tester = build_app_tester(None, entities.IncomeRollUpPeriod.PREVIOUS_MONTH)

    # Act
    app_tester.run()

    # Assert
    assert any("previous" in caption.value.lower() for caption in app_tester.caption)


def test_income_tab_stays_quiet_on_the_default_window(
    build_app_tester: "Callable[..., st_test.AppTest]",
) -> None:
    # Arrange - the current month is what the tab has always shown, so saying so
    # would be noise on every dashboard.
    app_tester = build_app_tester(None, entities.IncomeRollUpPeriod.CURRENT_MONTH)

    # Act
    app_tester.run()

    # Assert
    assert not any(
        "previous" in caption.value.lower() for caption in app_tester.caption
    )
