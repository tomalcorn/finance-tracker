"""Constants for the DFE module."""

import enum


class TableNames(enum.StrEnum):
    """Names of tables in the backend."""

    PAYMENTS = enum.auto()
    BANK_ACCOUNTS = enum.auto()
    BANK_ACCOUNTS_VIEW = enum.auto()
