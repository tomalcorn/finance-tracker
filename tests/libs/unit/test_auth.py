"""Unit tests for the auth module."""

import typing
import uuid
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

    _BT_IDS: typing.ClassVar[list[str]] = [str(uuid.uuid4()) for _ in range(4)]
    _BT_ROWS_ALL: typing.ClassVar[list[dict[str, object]]] = [
        {"id": _BT_IDS[0], "name": "Expenses"},
        {"id": _BT_IDS[1], "name": "Joint"},
        {"id": _BT_IDS[2], "name": "One-offs"},
        {"id": _BT_IDS[3], "name": "Savings"},
    ]

    @pytest.fixture
    def _mock_conn(self) -> typing.Generator[mock.MagicMock, None, None]:
        with mock.patch.object(data_client, "CONN") as conn:
            yield conn

    @staticmethod
    def _get_data_side_effect(
        bt_rows: list[dict[str, object]],
        es_rows: list[dict[str, object]] | None = None,
    ) -> typing.Callable[..., list[dict[str, object]]]:
        """Return a side_effect for get_data that serves different tables."""
        if es_rows is None:
            es_rows = []

        def _side_effect(
            table_name: str,
            query_string: str,
            **_: object,
        ) -> list[dict[str, object]]:
            if table_name == "budget_tracker":
                if "id" in query_string:
                    return bt_rows
                return [{"name": r["name"]} for r in bt_rows]
            if table_name == "expense_sources":
                return es_rows
            return []

        return _side_effect

    @pytest.mark.usefixtures("_mock_conn")
    def test_inserts_all_four_bt_when_none_exist(
        self,
    ) -> None:
        # First call returns empty (no BTs), re-fetch after insert returns all.
        call_count = 0

        def _side_effect(
            table_name: str,
            query_string: str,  # noqa: ARG001
            **_: object,
        ) -> list[dict[str, object]]:
            nonlocal call_count
            if table_name == "budget_tracker":
                call_count += 1
                if call_count <= 1:
                    return []
                return self._BT_ROWS_ALL
            return []

        with mock.patch.object(data_client, "get_data", side_effect=_side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        bt_call = conn.table("budget_tracker").upsert.call_args
        inserted = bt_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Expenses", "Joint", "One-offs", "Savings"}

    @pytest.mark.usefixtures("_mock_conn")
    def test_seeds_hidden_expense_sources(
        self,
    ) -> None:
        side_effect = self._get_data_side_effect(self._BT_ROWS_ALL, es_rows=[])
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        conn.table("budget_tracker").upsert.assert_not_called()
        es_call = conn.table("expense_sources").insert.call_args
        inserted = es_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Joint", "One-offs", "Savings"}
        assert all(row["user_id"] == "auth0|user1" for row in inserted)

    @pytest.mark.usefixtures("_mock_conn")
    def test_skips_existing_expense_sources(
        self,
    ) -> None:
        existing_es: list[dict[str, object]] = [
            {"budget_tracker_ids": [self._BT_IDS[1], self._BT_IDS[3]]},
        ]
        side_effect = self._get_data_side_effect(
            self._BT_ROWS_ALL,
            es_rows=existing_es,
        )
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        es_call = conn.table("expense_sources").insert.call_args
        inserted = es_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"One-offs"}

    @pytest.mark.usefixtures("_mock_conn")
    def test_no_inserts_when_fully_seeded(
        self,
    ) -> None:
        existing_es: list[dict[str, object]] = [
            {"budget_tracker_ids": [self._BT_IDS[1], self._BT_IDS[2], self._BT_IDS[3]]},
        ]
        side_effect = self._get_data_side_effect(
            self._BT_ROWS_ALL,
            es_rows=existing_es,
        )
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        conn.table("budget_tracker").upsert.assert_not_called()
        conn.table("expense_sources").insert.assert_not_called()
