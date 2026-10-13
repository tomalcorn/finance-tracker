"""Auth for the Streamlit UI.

Owns the user-facing side of identity: Auth0 login via ``st.user``. How the
backend proves that identity lives behind the
``ports.authentication.Authenticator`` port, applied by composition.
"""

import streamlit as st


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
