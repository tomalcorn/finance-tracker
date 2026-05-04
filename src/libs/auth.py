"""Authentication helpers for the finance tracker application.

Provides the current user's details for CRUD operations.
Currently returns a hardcoded user; will be replaced with real
authentication once the login page is fully implemented.
"""

import streamlit as st

from libs import ss_keys
from libs.models import backend_models

_HARDCODED_USER = backend_models.UserModel(
    first_name="Tom",
    last_name="Alcorn",
)


def get_current_user() -> backend_models.UserModel:
    """Return the currently logged-in user.

    Stores the user in session state so the identity is stable
    for the lifetime of the session.
    """
    if ss_keys.SSKeys.CURRENT_USER not in st.session_state:
        st.session_state[ss_keys.SSKeys.CURRENT_USER] = _HARDCODED_USER
    return st.session_state[ss_keys.SSKeys.CURRENT_USER]
