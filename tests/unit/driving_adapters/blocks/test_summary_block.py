"""Unit tests for the top-level summary block's rendering."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities, read_models

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_USER_ID = "auth0|test-user-1"

type _AppTesterBuilder = Callable[..., st_test.AppTest]


def _render_wrapper(
    bank_accounts: "Sequence[read_models.BankAccountView]",
    budget_trackers: "Sequence[read_models.BudgetTrackerView]",
    payments: "Sequence[read_models.PaymentView]",
) -> None:
    """Render the summary block for AppTest.

    The rows are injected via AppTest ``kwargs`` because from_function re-runs
    this body in a fresh namespace where module-level names aren't visible.
    """
    from driving_adapters.blocks import summary_block

    summary_block.render(bank_accounts, budget_trackers, payments)


@pytest.fixture(name="bank_accounts")
def _bank_accounts() -> "list[read_models.BankAccountView]":
    """Return one account holding a known balance."""
    return [
        read_models.BankAccountView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name="Current Account",
            starting_balance=1000.0,
            current_balance=1234.56,
        ),
    ]


@pytest.fixture(name="budget_trackers")
def _budget_trackers() -> "list[read_models.BudgetTrackerView]":
    """Return one tracker with a quarter of its budget left."""
    return [
        read_models.BudgetTrackerView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name=entities.BudgetTrackerName.EXPENSES,
            total_budget=800.0,
            current_month=600.0,
            remaining=200.0,
            progress=75.0,
            split=100.0,
        ),
    ]


@pytest.fixture(name="payments")
def _payments() -> "list[read_models.PaymentView]":
    """Return one expense payment dated today."""
    return [
        read_models.PaymentView(
            id=uuid.uuid4(),
            user_id=_USER_ID,
            name="Groceries",
            payment_date=datetime.datetime.now(tz=datetime.UTC).date(),
            payment_type="expense",
            expense=42.0,
            income=0.0,
            checked=False,
            bank_account_id=uuid.uuid4(),
        ),
    ]


@pytest.fixture(name="build_app_tester")
def _build_app_tester() -> "_AppTesterBuilder":
    """Return a builder for an AppTest rendering the block over given rows."""

    def _build(
        bank_accounts: "Sequence[read_models.BankAccountView] | None" = None,
        budget_trackers: "Sequence[read_models.BudgetTrackerView] | None" = None,
        payments: "Sequence[read_models.PaymentView] | None" = None,
    ) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "bank_accounts": bank_accounts or [],
                "budget_trackers": budget_trackers or [],
                "payments": payments or [],
            },
        )

    return _build


def test_render_shows_a_card_per_headline_figure(
    build_app_tester: "_AppTesterBuilder",
    bank_accounts: "list[read_models.BankAccountView]",
    budget_trackers: "list[read_models.BudgetTrackerView]",
    payments: "list[read_models.PaymentView]",
) -> None:
    # Arrange
    app_tester = build_app_tester(bank_accounts, budget_trackers, payments)

    # Act
    app_tester.run()

    # Assert
    assert [metric.label for metric in app_tester.metric] == [
        "Total Balance",
        "Remaining Budget",
        "Spent This Month",
    ]


def test_render_formats_the_figures_as_pounds(
    build_app_tester: "_AppTesterBuilder",
    bank_accounts: "list[read_models.BankAccountView]",
    budget_trackers: "list[read_models.BudgetTrackerView]",
    payments: "list[read_models.PaymentView]",
) -> None:
    # Arrange
    app_tester = build_app_tester(bank_accounts, budget_trackers, payments)

    # Act
    app_tester.run()

    # Assert
    assert [metric.value for metric in app_tester.metric] == [
        "£1,234.56",
        "£200.00",
        "£42.00",
    ]


def test_render_survives_an_empty_workspace(
    build_app_tester: "_AppTesterBuilder",
) -> None:
    # Arrange - a user who has added nothing yet still gets the block.
    app_tester = build_app_tester()

    # Act
    app_tester.run()

    # Assert
    assert not app_tester.exception


def test_remaining_budget_reports_its_share_of_the_total(
    build_app_tester: "_AppTesterBuilder",
    budget_trackers: "list[read_models.BudgetTrackerView]",
) -> None:
    # Arrange
    app_tester = build_app_tester(budget_trackers=budget_trackers)

    # Act
    app_tester.run()

    # Assert
    assert app_tester.metric[1].delta == "25% of £800.00"


def test_expenditure_hides_a_delta_that_has_not_moved(
    build_app_tester: "_AppTesterBuilder",
) -> None:
    # Arrange - a zero delta still draws an arrow, which reads as movement on a
    # workspace that has recorded no payments at all.
    app_tester = build_app_tester()

    # Act
    app_tester.run()

    # Assert - Streamlit renders an omitted delta as an empty string.
    assert not app_tester.metric[2].delta


def test_remaining_budget_says_so_when_nothing_is_budgeted(
    build_app_tester: "_AppTesterBuilder",
) -> None:
    # Arrange - dividing by a zero total budget would blow up the whole block.
    app_tester = build_app_tester()

    # Act
    app_tester.run()

    # Assert
    assert app_tester.metric[1].delta == "no budget set"
