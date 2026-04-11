"""Fixtures for integration tests."""

import pytest
import st_supabase_connection
import streamlit as st


@pytest.fixture(autouse=True, scope="module")
def _clean_users_table() -> None:
    """Remove any rows left over from a previous failed test run."""
    connection: st_supabase_connection.SupabaseConnection = st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )
    connection.table("users").delete().neq(
        "id",
        "00000000-0000-0000-0000-000000000000",
    ).execute()
