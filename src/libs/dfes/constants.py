"""Constants for the DFE module."""

import enum


class TableNames(enum.StrEnum):
    """Names of tables in the backend."""

    PAYMENTS = enum.auto()
    BANK_ACCOUNTS = enum.auto()
    BANK_ACCOUNTS_VIEW = enum.auto()
    BUDGET_TRACKER = enum.auto()
    BUDGET_TRACKER_VIEW = enum.auto()
    EXPENSE_SOURCES = enum.auto()
    EXPENSE_SOURCES_VIEW = enum.auto()
    INCOME_SOURCES = enum.auto()
    INCOME_SOURCES_VIEW = enum.auto()
