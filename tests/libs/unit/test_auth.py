"""Unit tests for the auth module."""

import typing
from unittest import mock

import pytest

from libs import auth, data_client, ss_keys
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
            mock.patch.object(auth, "_seed_default_budget_trackers"),
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

    def test_seeds_budget_trackers_on_first_login(self) -> None:
        fake_user = mock.MagicMock(
            is_logged_in=True,
            sub="auth0|stub123",
            name="Stub User",
        )
        fake_user.get = mock.MagicMock(return_value="Stub User")

        with (
            mock.patch("streamlit.user", fake_user),
            mock.patch.object(auth, "_authenticate_supabase"),
            mock.patch.object(
                auth,
                "_seed_default_budget_trackers",
            ) as mock_seed,
        ):
            auth.get_current_user()
            mock_seed.assert_called_once_with("auth0|stub123")


class TestSeedDefaultBudgetTrackers:
    """Tests for _seed_default_budget_trackers."""

    @pytest.fixture
    def _mock_conn(self) -> typing.Generator[mock.MagicMock, None, None]:
        with mock.patch.object(data_client, "CONN") as conn:
            yield conn

    def test_inserts_all_four_when_none_exist(
        self,
        _mock_conn: mock.MagicMock,
    ) -> None:
        with mock.patch.object(data_client, "get_data", return_value=[]):
            auth._seed_default_budget_trackers("auth0|user1")

        call_args = _mock_conn.table("budget_tracker").upsert.call_args
        inserted = call_args[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Expenses", "Joint", "One-offs", "Savings"}
        assert all(row["user_id"] == "auth0|user1" for row in inserted)

    def test_inserts_only_missing(self, _mock_conn: mock.MagicMock) -> None:
        existing = [{"name": "Expenses"}, {"name": "Savings"}]
        with mock.patch.object(data_client, "get_data", return_value=existing):
            auth._seed_default_budget_trackers("auth0|user1")

        call_args = _mock_conn.table("budget_tracker").upsert.call_args
        inserted = call_args[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Joint", "One-offs"}

    def test_no_insert_when_all_exist(self, _mock_conn: mock.MagicMock) -> None:
        existing = [
            {"name": "Expenses"},
            {"name": "Joint"},
            {"name": "One-offs"},
            {"name": "Savings"},
        ]
        with mock.patch.object(data_client, "get_data", return_value=existing):
            auth._seed_default_budget_trackers("auth0|user1")

        _mock_conn.table("budget_tracker").upsert.assert_not_called()
