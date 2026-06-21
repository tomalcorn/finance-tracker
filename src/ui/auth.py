"""Authentication helpers for the finance tracker application.

Bridges Auth0 identity (via st.login / st.user) to Supabase RLS
by minting a custom JWT containing the Auth0 user ID.
"""

import time

import jwt
import st_supabase_connection
import streamlit as st

from domain import entities

# Budget tracker names that need a corresponding hidden expense source.
_HIDDEN_EXPENSE_SOURCE_BT_NAMES = (
    entities.BudgetTrackerName.JOINT,
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
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


def authenticate_supabase(
    auth0_sub: str,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> st_supabase_connection.SupabaseConnection:
    """Mint a Supabase JWT for the Auth0 user and apply it to the connection.

    Args:
        auth0_sub: The Auth0 user ID (``sub`` claim).
        connection: The Supabase connection to authenticate. Defaults to the
            shared Supabase connection for this session.

    Returns:
        The authenticated Supabase connection.

    """
    connection = connection or st.connection(
        "supabase", type=st_supabase_connection.SupabaseConnection,
    )
    token = _mint_supabase_jwt(auth0_sub)
    connection.client.postgrest.auth(token)
    return connection


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
