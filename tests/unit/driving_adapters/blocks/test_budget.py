"""Unit tests for the budget area's master list, detail panel and grids."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

import pytest
import streamlit.testing.v1 as st_test

from domain import entities, read_models
from driving_adapters.components.buttons import contribute_button
from use_cases.bank_one_offs import BankOneOffsUseCase
from use_cases.contribute_to_joint import ContributeToJointUseCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest

    from driving_adapters.blocks.budget import context as context_mod


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


@pytest.fixture(name="build_category")
def _build_category() -> "Callable[..., read_models.CategoryView]":
    """Return a builder for a category view row, a root unless given a parent."""

    def _build(
        name: str = "Groceries",
        parent_id: str | None = None,
        accrual: entities.AccrualPeriod = entities.AccrualPeriod.MONTHLY,
        budget: float = 100.0,
    ) -> "read_models.CategoryView":
        return read_models.CategoryView.model_validate(
            {
                "id": uuid.uuid4(),
                "user_id": "auth0|test-user-1",
                "name": name,
                "parent_id": parent_id,
                "budget": budget,
                "accrual": accrual,
                "accrued": 0.0,
                "remaining": budget,
                "progress": 0.0,
                "split": 0.0,
                "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            },
        )

    return _build


@pytest.fixture(name="bank_use_case")
def _bank_use_case(
    build_repo: "conftest.RepoBuilder",
    build_payment_repo: "conftest.PaymentRepoBuilder",
) -> BankOneOffsUseCase:
    """Return a banking use case over fakes; no render test drives it."""
    return BankOneOffsUseCase(
        category_repo=build_repo(),
        payment_repo=build_payment_repo("auth0|test-user-1"),
    )


@pytest.fixture(name="build_area")
def _build_area(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
    bank_use_case: BankOneOffsUseCase,
) -> "Callable[..., context_mod.BudgetArea]":
    """Return a builder for a BudgetArea over stub sources.

    A test overrides only what it varies — the categories on the page, the
    income sources, the roll-up period, the contribute button — and inherits
    the rest.
    """

    def _build(
        categories: "list[read_models.CategoryView] | None" = None,
        income: "list[read_models.IncomeSourceView] | None" = None,
        period: entities.IncomeRollUpPeriod = (
            entities.IncomeRollUpPeriod.CURRENT_MONTH
        ),
        contribute: "contribute_button.ContributeButton | None" = None,
    ) -> "context_mod.BudgetArea":
        from driving_adapters.blocks.budget import context

        rows = categories or []
        category_source = build_stub_data_source(rows)
        return context.BudgetArea(
            sources=context.BudgetTrackerSources(
                categories=category_source,
                income_sources=build_stub_data_source(income or []),
            ),
            budget_tracker_map={
                str(row.id): str(row.name) for row in rows if row.is_root
            },
            bank_account_map={},
            bank_one_offs_use_case=bank_use_case,
            income_roll_up_period=period,
            contribute_button=contribute,
        )

    return _build


def _render_wrapper(area: "context_mod.BudgetArea") -> None:
    """Render the budget area for AppTest.

    The area is injected via AppTest ``kwargs`` because from_function re-runs
    this body in a fresh namespace where module-level names aren't visible.
    """
    from driving_adapters.blocks.budget import page

    page.render(area)


def _tester(
    area: "context_mod.BudgetArea",
    selected: str | None = None,
) -> st_test.AppTest:
    """Build an AppTest over the area, optionally with an entry pre-selected."""
    app_tester = st_test.AppTest.from_function(
        _render_wrapper,
        default_timeout=120,
        kwargs={"area": area},
    )
    if selected is not None:
        app_tester.session_state["budget_area_selected"] = selected
    return app_tester


@pytest.fixture(name="four_trackers")
def _four_trackers(
    build_category: "Callable[..., read_models.CategoryView]",
) -> list["read_models.CategoryView"]:
    """Return the four fixed budget trackers, deliberately out of order."""
    return [
        build_category(name=entities.BudgetTrackerName.SAVINGS),
        build_category(name=entities.BudgetTrackerName.ONE_OFFS),
        build_category(name=entities.BudgetTrackerName.EXPENSES),
        build_category(name=entities.BudgetTrackerName.JOINT),
    ]


def test_the_master_list_leads_with_income_then_the_allocation_panel(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - the list is ordered by the sequence the decisions happen in,
    # and the trackers are built out of order to prove it is not read order.
    from driving_adapters.blocks.budget import page

    area = build_area(categories=four_trackers)

    # Act
    entries = page.master_entries(area)

    # Assert
    assert [entry.label for entry in entries] == [
        "Income",
        "Budget trackers",
        entities.BudgetTrackerName.EXPENSES,
        entities.BudgetTrackerName.JOINT,
        entities.BudgetTrackerName.ONE_OFFS,
        entities.BudgetTrackerName.SAVINGS,
    ]


def test_the_page_opens_on_a_tracker_not_on_income(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - income and the panel are where a budget is set up; the trackers
    # are what the page is opened to look at day to day.
    from driving_adapters.blocks.budget import page

    area = build_area(categories=four_trackers)
    expenses = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.EXPENSES
    )

    # Act
    app_tester = _tester(area)
    app_tester.run()

    # Assert
    assert app_tester.session_state[page.SELECTED_KEY] == str(
        expenses.id,
    )


def test_a_trackers_subcategory_grid_shows_only_its_own_children(
    build_area: "Callable[..., context_mod.BudgetArea]",
    build_category: "Callable[..., read_models.CategoryView]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - every grid narrows the one category slice itself.
    from driving_adapters.blocks.budget import grids

    expenses = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.EXPENSES
    )
    savings = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.SAVINGS
    )
    mine = build_category(parent_id=str(expenses.id))
    theirs = build_category(name="Rainy day", parent_id=str(savings.id))
    area = build_area(categories=[*four_trackers, mine, theirs])
    config = grids.children_config(area, expenses)
    predicate = config.source.row_predicate
    if predicate is None:
        msg = "a tracker's grid must narrow the source to its own children"
        raise AssertionError(msg)

    # Act
    shown = [row for row in (mine, theirs, expenses) if predicate(row)]

    # Assert
    assert shown == [mine]


@pytest.mark.parametrize(
    ("tracker", "expected_accrual"),
    [
        (entities.BudgetTrackerName.SAVINGS, entities.AccrualPeriod.MONTHLY),
        (entities.BudgetTrackerName.ONE_OFFS, entities.AccrualPeriod.MULTI_MONTH),
    ],
)
def test_a_subcategory_is_parented_to_the_tracker_it_was_added_under(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    tracker: entities.BudgetTrackerName,
    expected_accrual: entities.AccrualPeriod,
) -> None:
    # Arrange - the parent and the accrual are derived from the tracker the
    # grid hangs under, which is what gives every tracker a working add button
    # rather than only the one the grid used to be wired to.
    from driving_adapters.blocks.budget import grids

    area = build_area(categories=four_trackers)
    root = next(row for row in four_trackers if row.name == tracker)

    # Act
    config = grids.children_config(area, root)

    # Assert
    assert config.source.extra_row_values == {
        "parent_id": str(root.id),
        "accrual": expected_accrual,
    }


@pytest.mark.parametrize(
    "tracker",
    [entities.BudgetTrackerName.EXPENSES, entities.BudgetTrackerName.ONE_OFFS],
)
def test_a_tracker_meant_to_be_broken_down_offers_an_add_button(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    tracker: entities.BudgetTrackerName,
) -> None:
    # Arrange - on the old page this was impossible for anything but Expenses:
    # the categories tab was hard-wired to it.
    root = next(row for row in four_trackers if row.name == tracker)
    area = build_area(categories=four_trackers)

    # Act
    app_tester = _tester(area, selected=str(root.id))
    app_tester.run()

    # Assert
    assert any(
        btn.key == f"categories_{root.id}_add_row_button" for btn in app_tester.button
    )


@pytest.mark.parametrize(
    "tracker",
    [entities.BudgetTrackerName.JOINT, entities.BudgetTrackerName.SAVINGS],
)
def test_a_one_pot_tracker_offers_nothing_to_break_it_down(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    tracker: entities.BudgetTrackerName,
) -> None:
    # Arrange - each of these is one pot of money, so it neither offers to add
    # a subcategory nor explains the absence of any.
    root = next(row for row in four_trackers if row.name == tracker)
    area = build_area(categories=four_trackers)

    # Act
    app_tester = _tester(area, selected=str(root.id))
    app_tester.run()

    # Assert
    assert all(
        [
            not any("add_row_button" in str(btn.key) for btn in app_tester.button),
            not any("subcategories" in cap.value for cap in app_tester.caption),
        ],
    )


def test_a_one_pot_tracker_still_shows_subcategories_it_somehow_has(
    build_area: "Callable[..., context_mod.BudgetArea]",
    build_category: "Callable[..., read_models.CategoryView]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - not offering to add one is a different thing from hiding one
    # that exists; a row must never be invisible because of where it sits.
    savings = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.SAVINGS
    )
    child = build_category(name="Rainy day", parent_id=str(savings.id))
    area = build_area(categories=[*four_trackers, child])

    # Act
    app_tester = _tester(area, selected=str(savings.id))
    app_tester.run()

    # Assert
    assert app_tester.dataframe


def test_a_trackers_own_budget_is_not_editable_from_its_detail(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - the budget has one home, the allocation panel. On the old page
    # the same number was editable from four separate tabs.
    expenses = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.EXPENSES
    )
    area = build_area(categories=four_trackers)

    # Act
    app_tester = _tester(area, selected=str(expenses.id))
    app_tester.run()

    # Assert
    assert not app_tester.number_input


def test_the_allocation_panel_gives_every_tracker_a_budget_input(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange
    from driving_adapters.blocks.budget import page

    area = build_area(categories=four_trackers)

    # Act
    app_tester = _tester(area, selected=page.TRACKERS_ENTRY)
    app_tester.run()

    # Assert
    assert len(app_tester.number_input) == len(four_trackers)


def test_setting_a_budget_writes_a_patch_through_the_port(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
) -> None:
    # Arrange - the panel replaced a grid, so it has to reach the same port the
    # grid's edits did rather than only redrawing itself.
    from driving_adapters.blocks.budget import page

    area = build_area(categories=four_trackers)
    source: Any = area.sources.categories
    expenses = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.EXPENSES
    )
    app_tester = _tester(area, selected=page.TRACKERS_ENTRY)
    app_tester.run()

    # Act
    app_tester.number_input[0].set_value(250.0).run()

    # Assert
    assert source.edits == [{str(expenses.id): {"budget": 250.0}}]


def test_the_contribute_button_sits_on_the_joint_trackers_detail(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    contribute_btn: contribute_button.ContributeButton,
) -> None:

    # Arrange - contributing funds joint from personal, so it belongs with the
    # tracker the money lands in rather than loose on the page.
    joint = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.JOINT
    )
    area = build_area(categories=four_trackers, contribute=contribute_btn)

    # Act
    app_tester = _tester(area, selected=str(joint.id))
    app_tester.run()

    # Assert
    assert any(btn.key == "contribute_button" for btn in app_tester.button)


def test_no_contribute_button_on_another_trackers_detail(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    contribute_btn: contribute_button.ContributeButton,
) -> None:
    # Arrange
    expenses = next(
        row for row in four_trackers if row.name == entities.BudgetTrackerName.EXPENSES
    )
    area = build_area(categories=four_trackers, contribute=contribute_btn)

    # Act
    app_tester = _tester(area, selected=str(expenses.id))
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
def test_the_income_roll_up_column_is_labelled_for_its_month(
    build_area: "Callable[..., context_mod.BudgetArea]",
    period: entities.IncomeRollUpPeriod,
    expected_label: str,
) -> None:
    # Arrange - one column showing one of two months, so it is named for
    # whichever the settings put it on.
    from driving_adapters.blocks.budget import grids

    area = build_area(period=period)

    # Act
    config = grids.income_config(area)

    # Assert
    column = next(
        col for col in config.display.columns if col.column_name == "current_month"
    )
    assert column.column_config.get("label") == expected_label


def test_a_moved_roll_up_window_is_explained_on_the_column(
    build_area: "Callable[..., context_mod.BudgetArea]",
) -> None:
    # Arrange - only a moved window needs explaining.
    from driving_adapters.blocks.budget import grids

    area = build_area(period=entities.IncomeRollUpPeriod.PREVIOUS_MONTH)

    # Act
    config = grids.income_config(area)

    # Assert
    column = next(
        col for col in config.display.columns if col.column_name == "current_month"
    )
    assert "previous" in (column.column_config.get("help") or "")


def test_the_default_roll_up_window_needs_no_explaining(
    build_area: "Callable[..., context_mod.BudgetArea]",
) -> None:
    # Arrange
    from driving_adapters.blocks.budget import grids

    area = build_area(period=entities.IncomeRollUpPeriod.CURRENT_MONTH)

    # Act
    config = grids.income_config(area)

    # Assert
    column = next(
        col for col in config.display.columns if col.column_name == "current_month"
    )
    assert column.column_config.get("help") is None


@pytest.mark.parametrize(
    ("tracker", "expected_label"),
    [
        (entities.BudgetTrackerName.EXPENSES, "Share of Budget"),
        (entities.BudgetTrackerName.ONE_OFFS, "Share of Remaining"),
    ],
)
def test_the_split_column_is_named_for_what_it_measures_against(
    build_area: "Callable[..., context_mod.BudgetArea]",
    four_trackers: list["read_models.CategoryView"],
    tracker: entities.BudgetTrackerName,
    expected_label: str,
) -> None:
    # Arrange - a pot's denominator is what its tracker has left to allocate
    # this month (#262); a monthly category's is its tracker's whole budget.
    # The label is the only place a reader is told which one they are looking
    # at, and the two column sets must not drift onto the same wording.
    from driving_adapters.blocks.budget import grids

    area = build_area(categories=four_trackers)
    root = next(row for row in four_trackers if row.name == tracker)

    # Act
    config = grids.children_config(area, root)

    # Assert - the add dialog labels the field from `button_label`, so the two
    # have to agree or the same figure is named twice over.
    (split_column,) = [
        column for column in config.display.columns if column.column_name == "split"
    ]
    assert all(
        [
            split_column.column_config["label"] == expected_label,
            split_column.button_label == expected_label,
        ],
    )
