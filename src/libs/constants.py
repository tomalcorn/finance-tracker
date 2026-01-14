"""Enums and constants for the finance tracker application."""

import enum

MAX_UNIQUE_VALUES = 20


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    CURRENT_USER = enum.auto()
    COL_CONFIGS = enum.auto()
    WORKING_DF = enum.auto()
    CURRENT_DF = enum.auto()
    ADDED_ROWS = enum.auto()
    DELETED_ROWS = enum.auto()
    EDITED_ROWS = enum.auto()
    ROW_IDS = enum.auto()
    PREV_ADDED_ROWS = enum.auto()


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()
