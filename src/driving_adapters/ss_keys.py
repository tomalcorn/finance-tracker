"""Session state keys for the finance tracker application."""

import enum


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    WORKSPACE_INITIALISED = enum.auto()
    AUTH_CREDENTIALS_EXP = enum.auto()
    COL_CONFIGS = enum.auto()
    PREV_CONFIGS = enum.auto()
    ADDED_ROWS = enum.auto()
    DELETED_ROWS = enum.auto()
    EDITED_ROWS = enum.auto()
    BACKEND_UPDATES = enum.auto()
    NEW_DATA_ADDED = enum.auto()
