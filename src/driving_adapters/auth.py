"""Auth for the Streamlit UI.

Owns the user-facing side of identity: Auth0 login via ``st.user`` and keeping
the session's backend credentials fresh. How the backend actually proves
identity lives behind the ``ports.authentication.Authenticator`` port, so
swapping the persistence backend does not touch this module.
"""

import datetime
from typing import TYPE_CHECKING

import streamlit as st

from driving_adapters import ss_keys

if TYPE_CHECKING:
    from ports import authentication

# Re-authenticate once credentials are within this margin of expiry, so a live
# session never carries a credential the backend is about to reject.
_REFRESH_MARGIN = datetime.timedelta(minutes=5)


def ensure_authenticated(
    authenticator: "authentication.Authenticator",
    user_id: str,
) -> None:
    """Guarantee the session holds valid backend credentials.

    Safe to call on every script rerun: re-authenticates only when the session
    has no credentials yet or the tracked expiry is within ``_REFRESH_MARGIN``.

    Args:
        authenticator: The port that authenticates the backend for a user.
        user_id: The identity to authenticate as.

    """
    if ss_keys.SSKeys.AUTH_CREDENTIALS_EXP not in st.session_state:
        _authenticate(authenticator, user_id)
        return

    expires_at = st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP]
    now = datetime.datetime.now(tz=datetime.UTC)
    if expires_at is not None and expires_at - now <= _REFRESH_MARGIN:
        _authenticate(authenticator, user_id)


def _authenticate(
    authenticator: "authentication.Authenticator",
    user_id: str,
) -> None:
    """Authenticate and record the returned expiry in session state."""
    st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP] = authenticator.authenticate(
        user_id,
    )


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
