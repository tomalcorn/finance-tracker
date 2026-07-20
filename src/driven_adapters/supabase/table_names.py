"""Supabase table and view name constants.

These are an implementation detail of the Supabase adapter.
Nothing outside driven_adapters/supabase/ should import from here.
"""

import enum


class TableNames(enum.StrEnum):
    """Write-able table names in the Supabase schema."""

    PAYMENTS = enum.auto()
    BANK_ACCOUNTS = enum.auto()
    BUDGET_TRACKER = enum.auto()
    EXPENSE_SOURCES = enum.auto()
    ONE_OFFS = enum.auto()
    INCOME_SOURCES = enum.auto()
    SUBSCRIPTIONS = enum.auto()
    JOINT_ACCOUNTS = enum.auto()
    JOINT_ACCOUNT_MEMBERS = enum.auto()


class ViewNames(enum.StrEnum):
    """Read-only view names in the Supabase schema.

    Views return joined/computed data that the raw tables don't expose.
    Repository read methods use these; write methods use TableNames.
    """

    BANK_ACCOUNTS = "bank_accounts_view"
    BUDGET_TRACKER = "budget_tracker_view"
    EXPENSE_SOURCES = "expense_sources_view"
    ONE_OFFS = "one_offs_view"
    INCOME_SOURCES = "income_sources_view"
    SUBSCRIPTIONS = "subscriptions_view"


VIEWS_AFFECTED_BY: dict[TableNames, list[ViewNames]] = {
    TableNames.PAYMENTS: [
        ViewNames.BANK_ACCOUNTS,
        ViewNames.EXPENSE_SOURCES,
        ViewNames.INCOME_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    TableNames.BANK_ACCOUNTS: [ViewNames.BANK_ACCOUNTS],
    TableNames.EXPENSE_SOURCES: [
        ViewNames.EXPENSE_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    TableNames.INCOME_SOURCES: [
        ViewNames.INCOME_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    TableNames.SUBSCRIPTIONS: [ViewNames.SUBSCRIPTIONS],
    TableNames.ONE_OFFS: [ViewNames.ONE_OFFS],
    TableNames.BUDGET_TRACKER: [
        ViewNames.ONE_OFFS,
        ViewNames.EXPENSE_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    # JOINT_ACCOUNTS and JOINT_ACCOUNT_MEMBERS feed no views: the aggregate
    # views surface each row's own ownership_type / joint_account_id columns but
    # never join the joint tables, so a write to them invalidates no view.
}
