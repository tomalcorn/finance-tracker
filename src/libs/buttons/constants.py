"""Constants for buttons."""

import enum

ADD_FILTER_BUTTON_WIDTHS = [0.05, 0.05, 0.9]
MAX_UNIQUE_VALUES = 20


class ButtonIcons:
    """Icons for different buttons."""

    ADD = ":material/add_2:"
    FILTER = ":material/filter_list:"


class TabIcons(enum.StrEnum):
    """Material icon prefixes for tab labels."""

    OVERVIEW = ":material/dashboard:"
    TABLE = ":material/table:"
    BUDGET_TRACKER = ":material/grid_view:"
    EXPENSE = ":material/do_not_disturb_on:"
    INCOME = ":material/add_circle:"


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
