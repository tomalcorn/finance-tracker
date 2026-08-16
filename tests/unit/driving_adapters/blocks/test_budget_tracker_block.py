"""Unit tests for the budget tracker block's tabs, contribute button and income tab."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities, read_models
from driving_adapters.components.buttons import contribute_button
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

    from driving_adapters.components.dfes import data_source as data_source_mod
    from driving_adapters.models import frontend_models


@pytest.fixture(name="contribute_btn")
def _contribute_btn(
    build_repo: "conftest.RepoBuilder",
) -> contribute_button.ContributeButton:
    """Return a ContributeButton whose use case never runs in the render tests."""
    use_case = ContributeToJointUseCase(
        user_id="auth0|test-user-1",
        personal_payment_repo=build_repo(),
        joint_payment_repo=build_repo(),
        category_repo=build_repo(),
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
    visible. One stub source stands in for all three tabs — the two category
    tabs share one in the app as well.
    """
    from driving_adapters.blocks import budget_tracker_block

    sources = budget_tracker_block.BudgetTrackerSources(source, source)
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
            {"root_categories_filter_button"} in columns,
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
        (entities.IncomeRollUpPeriod.CURRENT_MONTH, "Received This Month"),
        (entities.IncomeRollUpPeriod.PREVIOUS_MONTH, "Received Last Month"),
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
    sources = budget_tracker_block.BudgetTrackerSources(source, source)

    # Act
    _, _, income_config = budget_tracker_block._configs(sources, {}, period)

    # Assert
    roll_up_column = next(
        column
        for column in income_config.display.columns
        if column.column_name == "current_month"
    )
    assert roll_up_column.column_config["label"] == expected_label


def _income_roll_up_column(
    period: entities.IncomeRollUpPeriod,
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> "frontend_models.DFEColumnConfig":
    """Return the income tab's roll-up column config for a period."""
    from driving_adapters.blocks import budget_tracker_block

    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source)
    _, _, income_config = budget_tracker_block._configs(sources, {}, period)
    return next(
        column
        for column in income_config.display.columns
        if column.column_name == "current_month"
    )


def test_income_column_tooltip_explains_a_moved_roll_up_window(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange / Act
    column = _income_roll_up_column(
        entities.IncomeRollUpPeriod.PREVIOUS_MONTH,
        build_stub_data_source,
    )

    # Assert
    assert "previous" in column.column_config["help"].lower()


def test_income_column_has_no_tooltip_on_the_default_window(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the current month is what the tab has always shown, so a tooltip
    # explaining it would be noise on every dashboard.
    # Act
    column = _income_roll_up_column(
        entities.IncomeRollUpPeriod.CURRENT_MONTH,
        build_stub_data_source,
    )

    # Assert
    assert column.column_config.get("help") is None


@pytest.fixture(name="build_category")
def _build_category() -> "Callable[..., read_models.CategoryView]":
    """Return a builder for a category view row, a root unless given a parent."""

    def _build(
        name: str = "Groceries",
        parent_id: str | None = None,
        accrual: entities.AccrualPeriod = entities.AccrualPeriod.MONTHLY,
    ) -> "read_models.CategoryView":
        return read_models.CategoryView.model_validate(
            {
                "id": uuid.uuid4(),
                "user_id": "auth0|test-user-1",
                "name": name,
                "parent_id": parent_id,
                "budget": 100.0,
                "accrual": accrual,
                "accrued": 0.0,
                "remaining": 100.0,
                "progress": 0.0,
                "split": 0.0,
                "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            },
        )

    return _build


def _tab_predicates(
    root_map: dict[str, str],
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> "tuple[Callable[..., bool], Callable[..., bool]]":
    """Return the roots and children tabs' own row predicates."""
    from driving_adapters.blocks import budget_tracker_block

    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source)
    roots_config, children_config, _ = budget_tracker_block._configs(
        sources,
        root_map,
        entities.IncomeRollUpPeriod.CURRENT_MONTH,
    )
    is_root = roots_config.source.row_predicate
    is_expense_child = children_config.source.row_predicate
    if is_root is None or is_expense_child is None:
        msg = "both category tabs must narrow the one source to their own slice"
        raise AssertionError(msg)
    return is_root, is_expense_child


def test_budget_tracker_tab_shows_only_roots(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - roots and children are rows of one table read through one
    # source, so each tab narrows it itself.
    expenses_root_id = str(uuid.uuid4())
    is_root, _ = _tab_predicates(
        {expenses_root_id: entities.BudgetTrackerName.EXPENSES},
        build_stub_data_source,
    )
    root = build_category(name=entities.BudgetTrackerName.EXPENSES)
    child = build_category(parent_id=expenses_root_id)

    # Act
    shown = [row for row in (root, child) if is_root(row)]

    # Assert
    assert shown == [root]


def test_expense_sources_tab_shows_only_children_of_the_expenses_root(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - a pot is a child too, but of the One-offs root, so only the
    # parent decides what this tab shows.
    expenses_root_id = str(uuid.uuid4())
    one_offs_root_id = str(uuid.uuid4())
    _, is_expense_child = _tab_predicates(
        {expenses_root_id: entities.BudgetTrackerName.EXPENSES},
        build_stub_data_source,
    )
    expense_child = build_category(parent_id=expenses_root_id)
    pot = build_category(
        parent_id=one_offs_root_id,
        accrual=entities.AccrualPeriod.MULTI_MONTH,
    )
    root = build_category(name=entities.BudgetTrackerName.EXPENSES)

    # Act
    shown = [row for row in (expense_child, pot, root) if is_expense_child(row)]

    # Assert
    assert shown == [expense_child]


def test_a_category_added_on_the_expense_sources_tab_is_parented_there(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the tab shows only that root's children, so a row added without
    # the parent would save as a root and appear not to persist.
    from driving_adapters.blocks import budget_tracker_block

    expenses_root_id = str(uuid.uuid4())
    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source)

    # Act
    _, children_config, _ = budget_tracker_block._configs(
        sources,
        {expenses_root_id: entities.BudgetTrackerName.EXPENSES},
        entities.IncomeRollUpPeriod.CURRENT_MONTH,
    )

    # Assert
    assert children_config.source.extra_row_values == {"parent_id": expenses_root_id}
