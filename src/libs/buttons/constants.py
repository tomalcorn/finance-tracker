"""Constants for buttons."""

import enum

ADD_FILTER_BUTTON_WIDTHS = [0.1, 0.1, 0.8]
MAX_UNIQUE_VALUES = 20


class ButtonIcons:
    """Icons for different buttons."""

    ADD = ":material/add_2:"
    FILTER = ":material/filter_list:"


class TabIcons(enum.StrEnum):
    """Material icon prefixes for tab labels."""

    OVERVIEW = ":material/dashboard: Overview"
    TABLE = ":material/table: Table"
    BUDGET_TRACKER = ":material/grid_view: Budget Tracker"
    EXPENSE_SOURCES = ":material/source: Expense Sources"
    INCOME_SOURCES = ":material/attach_money: Income Sources"
    EXPENSE_ENTRIES = ":material/shopping_cart: Expense Entries"
    INCOME_ENTRIES = ":material/monetization_on: Income Entries"


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
