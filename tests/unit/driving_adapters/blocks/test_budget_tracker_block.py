"""Unit tests for the budget tracker block's tabs, contribute button and income tab."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

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
    _, income_config = budget_tracker_block._configs(sources, {}, period)

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
    _, income_config = budget_tracker_block._configs(sources, {}, period)
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


def _expense_child_predicate(
    root_map: dict[str, str],
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> "Callable[..., bool]":
    """Return the expense categories tab's own row predicate."""
    from driving_adapters.blocks import budget_tracker_block

    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source)
    children_config, _ = budget_tracker_block._configs(
        sources,
        root_map,
        entities.IncomeRollUpPeriod.CURRENT_MONTH,
    )
    is_expense_child = children_config.source.row_predicate
    if is_expense_child is None:
        msg = "the categories tab must narrow the one source to its own slice"
        raise AssertionError(msg)
    return is_expense_child


def test_expense_categories_tab_shows_only_children_of_the_expenses_root(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_category: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - a pot is a child too, but of the One-offs root, so only the
    # parent decides what this tab shows.
    expenses_root_id = str(uuid.uuid4())
    one_offs_root_id = str(uuid.uuid4())
    is_expense_child = _expense_child_predicate(
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


def test_a_category_added_on_the_expense_categories_tab_is_parented_there(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the tab shows only that root's children, so a row added without
    # the parent would save as a root and appear not to persist.
    from driving_adapters.blocks import budget_tracker_block

    expenses_root_id = str(uuid.uuid4())
    source = build_stub_data_source()
    sources = budget_tracker_block.BudgetTrackerSources(source, source)

    # Act
    children_config, _ = budget_tracker_block._configs(
        sources,
        {expenses_root_id: entities.BudgetTrackerName.EXPENSES},
        entities.IncomeRollUpPeriod.CURRENT_MONTH,
    )

    # Assert
    assert children_config.source.extra_row_values == {"parent_id": expenses_root_id}


def _panel_wrapper(source: "data_source_mod.GridDataSource") -> None:
    """Render the allocation panel alone for AppTest.

    Injected via kwargs for the same reason as ``_render_wrapper``: from_function
    re-runs this body in a namespace where module-level names aren't visible.
    """
    from driving_adapters.blocks import budget_tracker_block

    sources = budget_tracker_block.BudgetTrackerSources(source, source)
    budget_tracker_block.render_allocation_panel(sources)


@pytest.fixture(name="build_panel_tester")
def _build_panel_tester(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    build_category: "Callable[..., read_models.CategoryView]",
) -> "Callable[..., tuple[st_test.AppTest, Any]]":
    """Return a builder for an AppTest over the panel, and the source behind it.

    The source is handed back so a test can assert on what the panel wrote
    through it.
    """

    def _build(
        *names: entities.BudgetTrackerName,
    ) -> "tuple[st_test.AppTest, Any]":
        source = build_stub_data_source(
            [build_category(name=name) for name in names],
        )
        app_tester = st_test.AppTest.from_function(
            _panel_wrapper,
            default_timeout=120,
            kwargs={"source": source},
        )
        return app_tester, source

    return _build


def test_the_panel_gives_every_tracker_its_own_budget_input(
    build_panel_tester: "Callable[..., tuple[st_test.AppTest, Any]]",
) -> None:
    # Arrange - one card per tracker, each with the one editable figure.
    trackers = (
        entities.BudgetTrackerName.EXPENSES,
        entities.BudgetTrackerName.SAVINGS,
    )
    app_tester, _ = build_panel_tester(*trackers)

    # Act
    app_tester.run()

    # Assert
    assert len(app_tester.number_input) == len(trackers)


def test_setting_a_budget_writes_a_patch_through_the_port(
    build_panel_tester: "Callable[..., tuple[st_test.AppTest, Any]]",
) -> None:
    # Arrange - the panel replaces a grid, so it has to reach the same port the
    # grid's edits did rather than only redrawing itself.
    app_tester, source = build_panel_tester(entities.BudgetTrackerName.EXPENSES)
    app_tester.run()

    root_id = str(source.rows()[0].id)

    # Act
    app_tester.number_input[0].set_value(250.0).run()

    # Assert
    assert source.edits == [{root_id: {"budget": 250.0}}]


def test_the_panel_orders_the_trackers_by_their_fixed_names(
    build_panel_tester: "Callable[..., tuple[st_test.AppTest, Any]]",
) -> None:
    # Arrange - built in the wrong order on purpose; the cards must not follow
    # whatever order the read happened to return.
    app_tester, _ = build_panel_tester(
        entities.BudgetTrackerName.SAVINGS,
        entities.BudgetTrackerName.EXPENSES,
    )

    # Act
    app_tester.run()

    # Assert
    named = [
        name
        for markdown in app_tester.markdown
        for name in entities.BudgetTrackerName
        if name in markdown.value
    ]
    assert named == [
        entities.BudgetTrackerName.EXPENSES,
        entities.BudgetTrackerName.SAVINGS,
    ]


def test_a_workspace_with_no_trackers_still_offers_the_contribute_button(
    build_app_tester: "Callable[..., st_test.AppTest]",
    contribute_btn: contribute_button.ContributeButton,
) -> None:
    # Arrange - contributing funds the joint account from personal; it is not
    # one of the panel's contents, so the empty state must not swallow it.
    app_tester = build_app_tester(contribute_btn)

    # Act
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_button" for btn in app_tester.button)
