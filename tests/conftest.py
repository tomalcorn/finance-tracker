"""Helper functions and fixtures for tests."""

import typing

import pytest
import st_supabase_connection
import streamlit as st
import streamlit.testing.v1 as st_test

from libs import backend_models, constants, frontend_models


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="yield_sample_user")
def _yield_sample_user(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[backend_models.UserModel, None, None]:
    """Set up a sample user for tests."""
    sample_user = backend_models.UserModel(first_name="Test", last_name="User")
    # Insert user into the test database
    connection.table("users").insert(sample_user.model_dump(mode="json")).execute()

    yield sample_user

    # Clean up the user from the test database
    connection.table("users").delete().eq("id", sample_user.id).execute()


def get_rendered_texts(app_tester: st_test.AppTest) -> list[str]:
    """Get all rendered texts from the app tester.

    Args:
        app_tester: The Streamlit app tester instance.

    Returns:
        A list of rendered texts.

    """
    texts = [t.value for t in getattr(app_tester, "text", [])]
    markdowns = [m.value for m in getattr(app_tester, "markdown", [])]
    return texts + markdowns


@pytest.fixture(name="col_configs")
def _col_configs() -> list[frontend_models.DFEColumnConfig]:
    return [
        frontend_models.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting=constants.SortingValues.ASCENDING,
            filtering=frontend_models.Filters(lte="2023-01-01", gte="2022-01-01"),
        ),
    ]
