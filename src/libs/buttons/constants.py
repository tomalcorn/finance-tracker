"""Constants for buttons."""

import enum

ADD_FILTER_BUTTON_WIDTHS = [0.1, 0.1, 0.8]
MAX_UNIQUE_VALUES = 20


class ButtonIcons:
    """Icons for different buttons."""

    ADD = ":material/add_2:"
    FILTER = ":material/filter_list:"


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
