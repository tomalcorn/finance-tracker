"""Authentication helpers for the finance tracker application.

Bridges Auth0 identity (via st.login / st.user) to Supabase RLS
by minting a custom JWT containing the Auth0 user ID.
"""

import time
import uuid
from typing import cast

import jwt
import streamlit as st

from libs import data_client
from libs.models import backend_models

# Budget tracker names that need a corresponding hidden expense source.
_HIDDEN_EXPENSE_SOURCE_BT_NAMES = (
    backend_models.BudgetTrackerName.JOINT,
    backend_models.BudgetTrackerName.ONE_OFFS,
    backend_models.BudgetTrackerName.SAVINGS,
)


def _mint_supabase_jwt(auth0_sub: str) -> str:
    """Mint a JWT that Supabase PostgREST will accept for RLS.

    The ``userId`` claim is read by the custom ``auth.user_id()``
    Postgres function used in RLS policies.
    """
    secret = str(st.secrets["supabase_admin"]["jwt_secret"])
    now = int(time.time())
    payload = {
        "userId": auth0_sub,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def authenticate_supabase_and_seed_default_budget_trackers(auth0_sub: str) -> None:
    """Set a custom JWT on the Supabase connection and seed defaults."""
    token = _mint_supabase_jwt(auth0_sub)
    data_client.CONN.client.postgrest.auth(token)

    # Create the four default budget tracker rows and hidden expense sources.
    # --- seed budget trackers ---
    bt_rows = data_client.get_data(
        table_name="budget_tracker",
        query_string="id,name",
    )
    existing_bt_names = {str(row["name"]) for row in bt_rows}

    missing_bts = [
        backend_models.BudgetTrackerItemModel(
            user_id=auth0_sub,
            name=name,
        ).model_dump(mode="json")
        for name in backend_models.BudgetTrackerName
        if name.value not in existing_bt_names
    ]
    if missing_bts:
        data_client.CONN.table("budget_tracker").upsert(
            missing_bts,
            on_conflict="user_id,name",
        ).execute()
        data_client.invalidate_table_cache("budget_tracker")
        # Re-fetch so we have IDs for the newly created rows.
        bt_rows = data_client.get_data(
            table_name="budget_tracker",
            query_string="id,name",
        )

    # --- seed hidden expense sources for Joint / One-offs / Savings ---
    bt_id_by_name: dict[str, str] = {str(r["name"]): str(r["id"]) for r in bt_rows}

    es_rows = data_client.get_data(
        table_name="expense_sources",
        query_string="budget_tracker_ids",
    )
    existing_bt_links: set[str] = set()
    for row in es_rows:
        for bt_id in cast("list[str]", row.get("budget_tracker_ids") or []):
            existing_bt_links.add(str(bt_id))

    missing_es = [
        backend_models.ExpenseSourceModel(
            user_id=auth0_sub,
            name=name.value,
            budget_tracker_ids=[uuid.UUID(bt_id_by_name[name.value])],
        ).model_dump(mode="json")
        for name in _HIDDEN_EXPENSE_SOURCE_BT_NAMES
        if name.value in bt_id_by_name
        and bt_id_by_name[name.value] not in existing_bt_links
    ]
    if missing_es:
        data_client.CONN.table("expense_sources").insert(missing_es).execute()
        data_client.invalidate_table_cache("expense_sources")


def get_current_user() -> str:
    """Return the currently logged-in user.

    Reads the Auth0 identity from ``st.user`` and returns the user id.
    """
    if not st.user.is_logged_in:
        st.error("Not logged in.")
        st.stop()

    if not isinstance((user_id := st.user.sub), str):
        msg = f"user_id is incorrect, expected str, found: {type(user_id)}"
        raise TypeError(msg)

    return user_id


def is_logged_in() -> bool:
    """Check whether a user is currently logged in."""
    return bool(st.user.is_logged_in)


def logout() -> None:
    """Clear all session state and caches, then trigger OIDC logout."""
    st.session_state.clear()
    st.cache_data.clear()
    st.logout()
