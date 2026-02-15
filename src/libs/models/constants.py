"""Enums and constants for the finance tracker application."""

import enum

MAX_UNIQUE_VALUES = 20
ADD_FILTER_BUTTON_WIDTHS = [0.2, 0.6, 0.2]


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    CURRENT_USER = enum.auto()
    COL_CONFIGS = enum.auto()
    WORKING_DF = enum.auto()
    PREV_CONFIGS = enum.auto()
    ADDED_ROWS = enum.auto()
    DELETED_ROWS = enum.auto()
    EDITED_ROWS = enum.auto()
    BACKEND_UPDATES = enum.auto()
    NEW_DATA_ADDED = enum.auto()


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
