"""Integration tests for the auth module against the test Supabase DB."""

import typing

import pytest
import st_supabase_connection

from libs import data_client

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
