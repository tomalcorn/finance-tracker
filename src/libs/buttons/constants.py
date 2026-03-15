"""Constants for buttons."""

import enum

ADD_FILTER_BUTTON_WIDTHS = [0.2, 0.6, 0.2]
MAX_UNIQUE_VALUES = 20


class ButtonIcons:
    """Icons for different buttons."""

    ADD = ":material/add_2:"
    FILTER = ":material/filter_list:"


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
