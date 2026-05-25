"""Authentication helpers for the finance tracker application.

Bridges Auth0 identity (via st.login / st.user) to Supabase RLS
by minting a custom JWT containing the Auth0 user ID.
"""

import time

import jwt
import streamlit as st

from libs import data_client, ss_keys
from libs.models import backend_models


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


def _authenticate_supabase(auth0_sub: str) -> None:
    """Set a custom JWT on the Supabase connection for RLS."""
    token = _mint_supabase_jwt(auth0_sub)
    data_client.CONN.client.postgrest.auth(token)


def _seed_default_budget_trackers(auth0_sub: str) -> None:
    """Create the four default budget tracker rows if they don't already exist."""
    existing = data_client.get_data(
        table_name="budget_tracker",
        query_string="name",
    )
    existing_names = {str(row["name"]) for row in existing}

    missing = [
        backend_models.BudgetTrackerItemModel(
            user_id=auth0_sub,
            name=name.value,
        ).model_dump(mode="json")
        for name in backend_models.BudgetTrackerName
        if name.value not in existing_names
    ]
    if missing:
        data_client.CONN.table("budget_tracker").upsert(
            missing,
            on_conflict="user_id,name",
        ).execute()
        data_client.invalidate_table_cache("budget_tracker")


def get_current_user() -> backend_models.UserModel:
    """Return the currently logged-in user.

    On first call per session, reads the Auth0 identity from ``st.user``,
    mints a Supabase JWT, and stores the user in session state.
    """
    if ss_keys.SSKeys.CURRENT_USER not in st.session_state:
        if not st.user.is_logged_in:
            st.error("Not logged in.")
            st.stop()

        auth0_sub = str(st.user.sub)
        name = str(st.user.get("name", auth0_sub))
        parts = name.split(" ", 1) if name else [auth0_sub, ""]
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        _authenticate_supabase(auth0_sub)
        _seed_default_budget_trackers(auth0_sub)

        st.session_state[ss_keys.SSKeys.CURRENT_USER] = backend_models.UserModel(
            id=auth0_sub,
            first_name=first_name,
            last_name=last_name,
        )

    return st.session_state[ss_keys.SSKeys.CURRENT_USER]


def is_logged_in() -> bool:
    """Check whether a user is currently logged in."""
    return bool(st.user.is_logged_in)


def logout() -> None:
    """Clear all session state and caches, then trigger OIDC logout."""
    st.session_state.clear()
    st.cache_data.clear()
    st.logout()
