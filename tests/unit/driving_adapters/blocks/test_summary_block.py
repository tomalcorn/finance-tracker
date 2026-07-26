"""Unit tests for the top-level summary block's rendering."""

from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from use_cases import summarise_finances

if TYPE_CHECKING:
    from collections.abc import Callable

type _AppTesterBuilder = Callable[..., st_test.AppTest]


def _render_wrapper(figures: "summarise_finances.FinanceSummary") -> None:
    """Render the summary block for AppTest.

    The figures are injected via AppTest ``kwargs`` because from_function
    re-runs this body in a fresh namespace where module-level names aren't
    visible — which is also why the annotation is quoted rather than evaluated.
    """
    from driving_adapters.blocks import summary_block

    summary_block.render(figures)


@pytest.fixture(name="build_figures")
def _build_figures() -> "Callable[..., summarise_finances.FinanceSummary]":
    """Return a builder for the summary the block renders."""

    def _build(
        total_balance: float = 1234.56,
        total_budget: float = 800.0,
        remaining_budget: float = 200.0,
        expenditure: float = 42.0,
        expenditure_history: list[float] | None = None,
    ) -> summarise_finances.FinanceSummary:
        return summarise_finances.FinanceSummary(
            total_balance=total_balance,
            balance_history=[1000.0, 1100.0, total_balance],
            total_budget=total_budget,
            remaining_budget=remaining_budget,
            expenditure=expenditure,
            expenditure_history=(
                [30.0, 35.0, expenditure]
                if expenditure_history is None
                else expenditure_history
            ),
        )

    return _build


@pytest.fixture(name="build_app_tester")
def _build_app_tester() -> "_AppTesterBuilder":
    """Return a builder for an AppTest rendering the block over given figures."""

    def _build(figures: summarise_finances.FinanceSummary) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={"figures": figures},
        )

    return _build


def test_render_shows_a_card_per_headline_figure(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange
    app_tester = build_app_tester(build_figures())

    # Act
    app_tester.run()

    # Assert
    assert [metric.label for metric in app_tester.metric] == [
        "Total Balance",
        "Remaining Budget",
        "Spent This Month",
    ]


def test_render_reports_each_figure(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange
    app_tester = build_app_tester(build_figures())

    # Act
    app_tester.run()

    # Assert - the raw figure is handed over; st.metric applies the format.
    assert [metric.value for metric in app_tester.metric] == [
        "1234.56",
        "200.0",
        "42.0",
    ]


def test_render_asks_for_pounds_on_every_card(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange - formatting happens client-side, so the contract worth pinning
    # is the format string each card is given.
    app_tester = build_app_tester(build_figures())

    # Act
    app_tester.run()

    # Assert
    assert {metric.proto.format for metric in app_tester.metric} == {"£%,.2f"}


def test_render_survives_an_empty_workspace(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange - a user who has added nothing yet still gets the block.
    app_tester = build_app_tester(
        build_figures(
            total_balance=0.0,
            total_budget=0.0,
            remaining_budget=0.0,
            expenditure=0.0,
            expenditure_history=[0.0, 0.0, 0.0],
        ),
    )

    # Act
    app_tester.run()

    # Assert
    assert not app_tester.exception


def test_remaining_budget_reports_its_share_of_the_total(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange
    app_tester = build_app_tester(build_figures())

    # Act
    app_tester.run()

    # Assert
    assert app_tester.metric[1].delta == "25% of £800.00"


def test_remaining_budget_says_so_when_nothing_is_budgeted(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange - dividing by a zero total budget would blow up the whole block.
    app_tester = build_app_tester(
        build_figures(total_budget=0.0, remaining_budget=0.0),
    )

    # Act
    app_tester.run()

    # Assert
    assert app_tester.metric[1].delta == "no budget set"


def test_expenditure_hides_a_delta_that_has_not_moved(
    build_app_tester: "_AppTesterBuilder",
    build_figures: "Callable[..., summarise_finances.FinanceSummary]",
) -> None:
    # Arrange - a zero delta still draws an arrow, which reads as movement
    # where there is none.
    app_tester = build_app_tester(
        build_figures(expenditure=42.0, expenditure_history=[30.0, 42.0, 42.0]),
    )

    # Act
    app_tester.run()

    # Assert - Streamlit renders an omitted delta as an empty string.
    assert not app_tester.metric[2].delta
