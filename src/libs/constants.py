"""Enums and constants for the finance tracker application."""

import enum

MAX_UNIQUE_VALUES = 20


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    CURRENT_USER = enum.auto()
    COL_CONFIGS = enum.auto()


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASCENDING = "asc"
    DESCENDING = "desc"
