"""Authentication helpers for the finance tracker application.

Provides the current user's details for CRUD operations.
Currently uses hardcoded credentials; will be replaced with real
authentication once the login page is fully implemented.
"""

import uuid

import streamlit as st
import supabase_auth

from libs import data_client, ss_keys
from libs.models import backend_models


def get_current_user() -> backend_models.UserModel:
    """Return the currently logged-in user.

    On first call, authenticates with Supabase using hardcoded
    credentials and stores the user in session state.
    """
    if ss_keys.SSKeys.CURRENT_USER not in st.session_state:
        _sign_in()
    return st.session_state[ss_keys.SSKeys.CURRENT_USER]


def is_logged_in() -> bool:
    """Check whether a user is currently logged in."""
    return ss_keys.SSKeys.CURRENT_USER in st.session_state


def _sign_in() -> None:
    """Authenticate with Supabase and store the user in session state."""
    credentials = supabase_auth.SignInWithEmailAndPasswordCredentials(
        email="tomalcorn777@icloud.com",
        password="jiwQij-kirwi3-hedtyk",  # noqa: S106
    )

    with st.spinner("Signing in..."):
        auth_resp = data_client.CONN.auth.sign_in_with_password(credentials)

        access_token = None
        user = None

        if hasattr(auth_resp, "session") and auth_resp.session:
            access_token = auth_resp.session.access_token
            user = auth_resp.user

        if not access_token or not user:
            st.error("Authentication failed. Please check your credentials.")
            st.stop()
            return

        data_client.CONN.client.postgrest.auth(access_token)

        user_id = uuid.UUID(user.id)
        user_row = (
            data_client.CONN.table("users")
            .select("first_name, last_name")
            .eq("id", str(user_id))
            .execute()
            .data
        )
        if user_row:
            first_name = user_row[0].get("first_name", "")
            last_name = user_row[0].get("last_name", "")
        else:
            first_name = user.email or ""
            last_name = ""

        st.session_state[ss_keys.SSKeys.CURRENT_USER] = backend_models.UserModel(
            id=user_id,
            first_name=first_name,
            last_name=last_name,
        )
