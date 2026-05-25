"""Unit tests for the auth module."""

import typing
from unittest import mock

import pytest

from libs import auth, ss_keys
from libs.models import backend_models


class TestGetCurrentUser:
    """Tests for get_current_user."""

    @pytest.fixture(autouse=True)
    def _clear_session(self) -> typing.Generator[None, None, None]:
        """Patch st.session_state to an empty dict for each test."""
        with mock.patch.dict("streamlit.session_state", {}, clear=True):
            yield

    @pytest.fixture
    def _stub_auth0_user(self) -> typing.Generator[None, None, None]:
        """Simulate an Auth0-authenticated user and bypass Supabase calls."""
        fake_user = mock.MagicMock(
            is_logged_in=True,
            sub="auth0|stub123",
            name="Stub User",
        )
        fake_user.get = mock.MagicMock(return_value="Stub User")

        with (
            mock.patch("streamlit.user", fake_user),
            mock.patch.object(auth, "_authenticate_supabase"),
        ):
            yield

    @pytest.mark.usefixtures("_stub_auth0_user")
    def test_returns_user_model(self) -> None:
        user = auth.get_current_user()
        assert isinstance(user, backend_models.UserModel)

    @pytest.mark.usefixtures("_stub_auth0_user")
    def test_returns_stable_identity(self) -> None:
        first = auth.get_current_user()
        second = auth.get_current_user()
        assert first is second

    @pytest.mark.usefixtures("_stub_auth0_user")
    def test_user_has_valid_id(self) -> None:
        user = auth.get_current_user()
        assert isinstance(user.id, str)
        assert user.id == "auth0|stub123"

    def test_does_not_overwrite_existing_session_user(self) -> None:
        existing = backend_models.UserModel(
            id="auth0|existing",
            first_name="Other",
            last_name="User",
        )
        import streamlit as st

        st.session_state[ss_keys.SSKeys.CURRENT_USER] = existing

        user = auth.get_current_user()
        assert user is existing
