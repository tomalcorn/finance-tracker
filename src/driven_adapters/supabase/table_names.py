"""Supabase table and view name constants.

These are an implementation detail of the Supabase adapter.
Nothing outside driven_adapters/supabase/ should import from here.
"""

import enum


class TableNames(enum.StrEnum):
    """Write-able table names in the Supabase schema."""

    PAYMENTS = enum.auto()
    BANK_ACCOUNTS = enum.auto()
    CATEGORIES = enum.auto()
    BUDGET_TRACKER = enum.auto()
    EXPENSE_SOURCES = enum.auto()
    ONE_OFFS = enum.auto()
    INCOME_SOURCES = enum.auto()
    SUBSCRIPTIONS = enum.auto()
    QUICK_BUTTONS = enum.auto()
    USER_SETTINGS = enum.auto()
    JOINT_ACCOUNTS = enum.auto()
    JOINT_ACCOUNT_MEMBERS = enum.auto()


class ViewNames(enum.StrEnum):
    """Read-only view names in the Supabase schema.

    Views return joined/computed data that the raw tables don't expose.
    Repository read methods use these; write methods use TableNames.
    """

    BANK_ACCOUNTS = "bank_accounts_view"
    BUDGET_TRACKER = "budget_tracker_view"
    CATEGORIES = "categories_view"
    EXPENSE_SOURCES = "expense_sources_view"
    ONE_OFFS = "one_offs_view"
    INCOME_SOURCES = "income_sources_view"
    SUBSCRIPTIONS = "subscriptions_view"


_PAYMENT_DERIVED_VIEWS: list[ViewNames] = [
    ViewNames.BANK_ACCOUNTS,
    ViewNames.CATEGORIES,
    ViewNames.EXPENSE_SOURCES,
    ViewNames.INCOME_SOURCES,
    ViewNames.BUDGET_TRACKER,
]
"""The views that sum payments, so any write to them restates all five."""


CACHE_KEYS_AFFECTED_BY: dict[TableNames, list[ViewNames | TableNames]] = {
    TableNames.PAYMENTS: [*_PAYMENT_DERIVED_VIEWS],
    TableNames.BANK_ACCOUNTS: [ViewNames.BANK_ACCOUNTS],
    TableNames.EXPENSE_SOURCES: [
        ViewNames.EXPENSE_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    TableNames.INCOME_SOURCES: [
        ViewNames.INCOME_SOURCES,
        ViewNames.BUDGET_TRACKER,
        # A root's `split` divides by total income, so restating income restates
        # it. A child's divides by its parent's budget and is unaffected — but
        # the key is per-table, not per-row.
        ViewNames.CATEGORIES,
    ],
    # payments.subscription_id is ON DELETE CASCADE (0001), so deleting a
    # subscription deletes its generated payments too — a write to `payments`
    # this repository never issues and would otherwise never bust. The payments
    # key and everything computed from it therefore hang off subscriptions as
    # well, or a deleted subscription's payments linger until the TTL.
    TableNames.SUBSCRIPTIONS: [
        ViewNames.SUBSCRIPTIONS,
        TableNames.PAYMENTS,
        *_PAYMENT_DERIVED_VIEWS,
    ],
    TableNames.ONE_OFFS: [ViewNames.ONE_OFFS],
    # A write at either level restates both: a child's spend rolls up into its
    # parent's current_month, and a parent's budget is the denominator of its
    # children's split. One key covers it — roots and children are rows of the
    # same view — and the tree never crosses the ownership split (a child is
    # owned exactly as its root is), so there is no cascade to declare in
    # CASCADES_ACROSS_OWNERSHIP.
    #
    # The other three are the repoint-to-parent trigger (0030): deleting a
    # category moves every payment, subscription and quick button attributed to
    # it up onto its parent — writes to three tables this repository never
    # issues and would otherwise never bust. Only what *reads* an attribution is
    # listed: the amounts are untouched, so no balance or income total moves,
    # which is why the payment-derived views other than categories_view stay out.
    TableNames.CATEGORIES: [
        ViewNames.CATEGORIES,
        TableNames.PAYMENTS,
        ViewNames.SUBSCRIPTIONS,
        TableNames.QUICK_BUTTONS,
    ],
    TableNames.BUDGET_TRACKER: [
        ViewNames.ONE_OFFS,
        ViewNames.EXPENSE_SOURCES,
        ViewNames.BUDGET_TRACKER,
    ],
    # A settings row is not summed into anything, but it decides which month
    # income_sources_view rolls its payments up over — and the `split` of
    # budget_tracker_view and of a root in categories_view divides by that
    # total — so changing one restates all three.
    TableNames.USER_SETTINGS: [
        ViewNames.INCOME_SOURCES,
        ViewNames.BUDGET_TRACKER,
        ViewNames.CATEGORIES,
    ],
    # QUICK_BUTTONS feeds no views: a button is a preset, not a transaction, so
    # nothing is computed from one until a tap writes the payment it describes.
    #
    # JOINT_ACCOUNTS and JOINT_ACCOUNT_MEMBERS feed no views: the aggregate
    # views surface each row's own ownership_type / joint_account_id columns but
    # never join the joint tables, so a write to them invalidates no view.
}


CASCADES_ACROSS_OWNERSHIP: dict[TableNames, list[ViewNames | TableNames]] = {
    # Deleting a personal subscription cascades away *joint* payment rows: a
    # joint contribution's income leg is owned by the joint account but carries
    # the personal subscription's id, so the FK reaches across the ownership
    # split that normally keeps one repository inside one half.
    #
    # This is the one place a personal write moves a joint row, so it is the one
    # place a personal repository has to bust a joint key — otherwise the other
    # member's page serves an income whose subscription is gone until the TTL.
    TableNames.SUBSCRIPTIONS: [TableNames.PAYMENTS, *_PAYMENT_DERIVED_VIEWS],
}
