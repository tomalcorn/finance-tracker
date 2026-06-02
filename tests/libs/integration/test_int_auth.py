"""Integration tests for the auth module against the test Supabase DB."""

import typing

import jwt
import pytest
import st_supabase_connection
import streamlit as st

from libs import auth, data_client
from libs.models import backend_models

_ZERO_UUID = "00000000-0000-0000-0000-000000000000"
_HIDDEN_NAMES = {"Joint", "One-offs", "Savings"}


@pytest.fixture(name="_clean_seed_tables")
def _clean_seed_tables(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[None, None, None]:
    """Empty the budget_tracker and expense_sources tables before and after.

    The test DB has RLS disabled, so ``get_data`` is not filtered per user.
    The seeding logic therefore needs these tables empty to seed a fresh user.
    """

    def _wipe() -> None:
        connection.table("expense_sources").delete().neq("id", _ZERO_UUID).execute()
        connection.table("budget_tracker").delete().neq("id", _ZERO_UUID).execute()
        data_client._get_data_cached.clear()

    _wipe()
    yield
    _wipe()


@pytest.fixture(name="restore_anon_auth")
def _restore_anon_auth(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[None, None, None]:
    """Restore the connection's original (anon) auth header after the test.

    Authenticating mutates the shared, cached testing connection. Without this
    reset, later integration tests would send a JWT the test project rejects.
    """
    headers = connection.client.postgrest.headers
    original = headers.get("Authorization")
    yield
    if original is not None:
        headers["Authorization"] = original
    else:
        headers.pop("Authorization", None)


@pytest.mark.usefixtures("_clean_seed_tables")
class TestSeedDefaultBudgetTrackersIntegration:
    """Integration tests for auth.seed_default_budget_trackers."""

    _USER_ID = "auth0|seed-int-test-user"

    def test_seeds_budget_trackers_and_hidden_expense_sources(
        self,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Seeding a fresh user creates the 4 BTs and 3 hidden expense sources."""
        # Act
        auth.seed_default_budget_trackers(self._USER_ID, connection=connection)

        # Assert — read directly to bypass the cache
        bt_rows = (
            connection.table("budget_tracker")
            .select("id,name")
            .eq("user_id", self._USER_ID)
            .execute()
            .data
        )
        es_rows = (
            connection.table("expense_sources")
            .select("name,budget_tracker_ids")
            .eq("user_id", self._USER_ID)
            .execute()
            .data
        )
        bt_id_by_name = {row["name"]: row["id"] for row in bt_rows}
        assert all(
            [
                {row["name"] for row in bt_rows}
                == {name.value for name in backend_models.BudgetTrackerName},
                {row["name"] for row in es_rows} == _HIDDEN_NAMES,
                all(
                    row["budget_tracker_ids"] == [bt_id_by_name[row["name"]]]
                    for row in es_rows
                ),
            ],
        )

    def test_seeding_is_idempotent(
        self,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Seeding twice does not create duplicate rows."""
        # Act
        auth.seed_default_budget_trackers(self._USER_ID, connection=connection)
        data_client._get_data_cached.clear()
        auth.seed_default_budget_trackers(self._USER_ID, connection=connection)

        # Assert — still exactly 4 budget trackers and 3 expense sources
        bt_rows = (
            connection.table("budget_tracker")
            .select("id")
            .eq("user_id", self._USER_ID)
            .execute()
            .data
        )
        es_rows = (
            connection.table("expense_sources")
            .select("id")
            .eq("user_id", self._USER_ID)
            .execute()
            .data
        )
        assert all(
            [
                len(bt_rows) == len(backend_models.BudgetTrackerName),
                len(es_rows) == len(_HIDDEN_NAMES),
            ],
        )


class TestAuthenticateSupabaseIntegration:
    """Integration tests for auth.authenticate_supabase."""

    _USER_ID = "auth0|auth-int-test-user"

    @pytest.mark.usefixtures("restore_anon_auth")
    def test_returns_authenticated_connection(
        self,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """The returned connection carries a valid bearer token for the user."""
        # Act
        returned = auth.authenticate_supabase(self._USER_ID, connection=connection)

        # Assert — same connection object, now carrying a valid bearer JWT whose
        # claims drive RLS.
        header = connection.client.postgrest.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ")
        secret = str(st.secrets["supabase_admin"]["jwt_secret"])
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        assert all(
            [
                returned is connection,
                header.startswith("Bearer "),
                claims["userId"] == self._USER_ID,
                claims["role"] == "authenticated",
            ],
        )
