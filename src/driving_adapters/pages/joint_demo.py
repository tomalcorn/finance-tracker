"""Throwaway demo page for verifying joint-account row-level security.

Reads back only what the logged-in user's RLS policies expose — their Auth0 id,
the joint accounts and memberships they can see, and any joint-owned rows across
the aggregates. Every read goes through the authenticated connection, so the
page is a direct manual check that the Joint Workflow RLS (#174) admits the right
rows and nothing else. Not part of the real UI; safe to delete with this branch.
"""

import st_supabase_connection
import streamlit as st

_JOINT_AGGREGATES = (
    ("Payments", "payments"),
    ("Bank accounts", "bank_accounts"),
    ("Expense sources", "expense_sources"),
    ("Income sources", "income_sources"),
    ("Budget tracker", "budget_tracker"),
    ("One-offs", "one_offs"),
    ("Subscriptions", "subscriptions"),
)


def _connection() -> st_supabase_connection.SupabaseConnection:
    """Return the session's authenticated Supabase connection (RLS applies)."""
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def _show_table(title: str, table: str, *, joint_only: bool = False) -> None:
    """Query one table through RLS and render the visible rows."""
    st.subheader(title)
    try:
        query = _connection().table(table).select("*")
        if joint_only:
            query = query.eq("ownership_type", "joint")
        rows = query.execute().data
    except Exception as exc:  # noqa: BLE001 - demo page surfaces any failure verbatim
        st.error(f"Query on {table!r} failed: {exc}")
        return
    st.caption(f"{len(rows)} row(s) visible")
    if rows:
        st.dataframe(rows, width="stretch")


st.title(":material/group: Joint RLS demo")
st.caption(
    "Throwaway page to verify joint-account row-level security. Every table below "
    "is read through your authenticated connection, so you see exactly what RLS "
    "admits — your own personal data plus joint rows for accounts you belong to.",
)

st.subheader("You")
st.write("Your Auth0 user id — use this as `user_id` when adding joint members:")
st.code(str(st.user.sub), language="text")

st.divider()
_show_table("Joint accounts (you are a member of)", "joint_accounts")
_show_table("Joint account members (visible to you)", "joint_account_members")

st.divider()
st.header("Joint-owned rows across aggregates")
st.caption("Rows with ownership_type = 'joint' that RLS lets you see.")
for label, table in _JOINT_AGGREGATES:
    _show_table(label, table, joint_only=True)
