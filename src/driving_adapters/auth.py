"""Authentication helpers for the finance tracker application.

Bridges Auth0 identity (via st.login / st.user) to Supabase RLS
by minting a custom JWT containing the Auth0 user ID.
"""

import time

import jwt
import st_supabase_connection
import streamlit as st

from driving_adapters import ss_keys

_TOKEN_TTL_SECONDS = 3600
# Re-mint once the token is within this many seconds of expiry, so a live
# session never carries a JWT that PostgREST is about to reject.
_REFRESH_MARGIN_SECONDS = 300


def _default_connection() -> st_supabase_connection.SupabaseConnection:
    """Return the shared Supabase connection for this session."""
    return st.connection(
        "supabase",
        type=st_supabase_connection.SupabaseConnection,
    )


def _mint_supabase_jwt(auth0_sub: str) -> tuple[str, int]:
    """Mint a JWT that Supabase PostgREST will accept for RLS.

    The ``userId`` claim is read by the custom ``auth.user_id()``
    Postgres function used in RLS policies.

    Returns:
        The encoded token and its ``exp`` (Unix seconds), so callers can track
        when it must be refreshed.

    """
    secret = str(st.secrets["supabase_admin"]["jwt_secret"])
    now = int(time.time())
    exp = now + _TOKEN_TTL_SECONDS
    payload = {
        "userId": auth0_sub,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm="HS256"), exp


def authenticate_supabase(
    auth0_sub: str,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> st_supabase_connection.SupabaseConnection:
    """Mint a fresh Supabase JWT for the Auth0 user and apply it to the connection.

    Records the token's expiry in session state so
    ``ensure_supabase_authenticated`` can refresh it before it lapses.

    Args:
        auth0_sub: The Auth0 user ID (``sub`` claim).
        connection: The Supabase connection to authenticate. Defaults to the
            shared Supabase connection for this session.

    Returns:
        The authenticated Supabase connection.

    """
    connection = connection or _default_connection()
    token, exp = _mint_supabase_jwt(auth0_sub)
    connection.client.postgrest.auth(token)
    st.session_state[ss_keys.SSKeys.SUPABASE_TOKEN_EXP] = exp
    return connection


def ensure_supabase_authenticated(
    auth0_sub: str,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> st_supabase_connection.SupabaseConnection:
    """Guarantee the connection carries a non-expired Supabase JWT.

    Safe to call on every script rerun: the connection keeps its token across
    reruns, so this only re-mints when no token has been issued yet or the
    tracked expiry is within ``_REFRESH_MARGIN_SECONDS``.

    Args:
        auth0_sub: The Auth0 user ID (``sub`` claim).
        connection: The Supabase connection to authenticate. Defaults to the
            shared Supabase connection for this session.

    Returns:
        The authenticated Supabase connection.

    """
    connection = connection or _default_connection()
    exp = st.session_state.get(ss_keys.SSKeys.SUPABASE_TOKEN_EXP)
    if exp is None or exp - int(time.time()) <= _REFRESH_MARGIN_SECONDS:
        return authenticate_supabase(auth0_sub, connection)
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
