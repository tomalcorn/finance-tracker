"""What the budget area is made of, and how to slice it.

Every grid on the page reads the one category slice already fetched and narrows
it here. A filtered read would be Path B and would need its own cache key.
"""

import dataclasses
from typing import TYPE_CHECKING

from domain import entities

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models
    from driving_adapters.components.buttons import (
        contribute_button as contribute_button_component,
    )
    from driving_adapters.components.dfes import data_source as data_source_mod
    from use_cases import bank_one_offs

ROOT_ICONS: dict[str, str] = {
    entities.BudgetTrackerName.EXPENSES: ":material/do_not_disturb_on:",
    entities.BudgetTrackerName.JOINT: ":material/group:",
    entities.BudgetTrackerName.ONE_OFFS: ":material/bubble_chart:",
    entities.BudgetTrackerName.SAVINGS: ":material/savings:",
}

# Each of these is one pot of money rather than something to break down, so
# neither offers to add a subcategory nor explains the absence of any.
TRACKERS_WITHOUT_SUBCATEGORIES = frozenset(
    {
        entities.BudgetTrackerName.JOINT,
        entities.BudgetTrackerName.SAVINGS,
    },
)


@dataclasses.dataclass(frozen=True)
class BudgetTrackerSources:
    """The grid data sources behind the budget area.

    Two sources for every grid on the page: the trackers, their subcategories
    and any orphan are three slices of the one category tree, and income is the
    other.
    """

    categories: "data_source_mod.GridDataSource[read_models.CategoryView]"
    income_sources: "data_source_mod.GridDataSource[read_models.IncomeSourceView]"


@dataclasses.dataclass(frozen=True)
class BudgetArea:
    """Everything the budget area needs to render itself."""

    sources: BudgetTrackerSources
    budget_tracker_map: dict[str, str]
    bank_account_map: dict[str, str]
    bank_one_offs_use_case: "bank_one_offs.BankOneOffsUseCase"
    income_roll_up_period: entities.IncomeRollUpPeriod = (
        entities.IncomeRollUpPeriod.CURRENT_MONTH
    )
    contribute_button: "contribute_button_component.ContributeButton | None" = None


def categories(area: BudgetArea) -> "Sequence[read_models.CategoryView]":
    """Return every category the user owns, roots and children alike."""
    return area.sources.categories.rows()


def roots(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return the budget trackers, in the fixed display order of their names."""
    order = list(entities.BudgetTrackerName)
    return sorted(
        (row for row in categories(area) if row.is_root),
        key=lambda row: order.index(row.name) if row.name in order else len(order),
    )


def children_of(area: BudgetArea, root_id: str) -> list["read_models.CategoryView"]:
    """Return the subcategories sitting under one tracker."""
    return [
        row
        for row in categories(area)
        if not row.is_root and str(row.parent_id) == root_id
    ]


def total_income(area: BudgetArea) -> float:
    """Return what the tracker budgets are being split out of."""
    return sum(row.current_month for row in area.sources.income_sources.rows())


def is_pot_root(root: "read_models.CategoryView") -> bool:
    """Whether this tracker's subcategories are pots rather than monthly."""
    return root.name == entities.BudgetTrackerName.ONE_OFFS


def takes_subcategories(root: "read_models.CategoryView") -> bool:
    """Whether this tracker is meant to be broken down at all."""
    return root.name not in TRACKERS_WITHOUT_SUBCATEGORIES


def bankable_pots(area: BudgetArea) -> list["read_models.CategoryView"]:
    """Return the pots with an amount planned for the current month.

    Read through the port rather than off the grid's display frame: banking acts
    on the aggregate, so neither an active column filter nor the sample data an
    empty frame falls back to gets to decide what is bankable.
    """
    return [row for row in categories(area) if row.is_pot and row.budget > 0]
