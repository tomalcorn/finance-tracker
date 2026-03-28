"""Helper functions and fixtures for tests."""

import typing
import uuid

import pytest
import st_supabase_connection
import streamlit as st
import streamlit.testing.v1 as st_test

from libs.buttons import constants
from libs.models import backend_models, frontend_models


@pytest.fixture(autouse=True)
def _clear_session_state() -> None:
    """Clear streamlit session state before each test."""
    st.session_state.clear()


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="sample_user")
def _sample_user() -> backend_models.UserModel:
    """Provide a sample user model for tests."""
    return backend_models.UserModel(first_name="Test", last_name="User1")


@pytest.fixture(name="yield_sample_user")
def _yield_sample_user(
    connection: st_supabase_connection.SupabaseConnection,
    sample_user: backend_models.UserModel,
) -> typing.Generator[backend_models.UserModel, None, None]:
    """Set up a sample user for tests."""
    connection.table("users").insert(sample_user.model_dump(mode="json")).execute()

    yield sample_user

    # Clean up the user from the test database
    connection.table("users").delete().eq("id", sample_user.id).execute()


@pytest.fixture(name="yield_sample_users")
def _yield_sample_users(
    sample_user: backend_models.UserModel,
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[list[backend_models.UserModel], None, None]:
    """Set up multiple sample users for tests."""
    sample_users = [
        sample_user,
        sample_user.model_copy(
            update={"id": uuid.uuid4(), "last_name": "User2"},
            deep=True,
        ),
    ]
    # Insert users into the test database
    for user in sample_users:
        connection.table("users").insert(user.model_dump(mode="json")).execute()

    yield sample_users

    # Clean up the users from the test database
    for user in sample_users:
        connection.table("users").delete().eq("id", user.id).execute()


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
def _col_configs() -> list[frontend_models.DFEColumnConfigBase]:
    return [
        frontend_models.DFEColumnConfigBase(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting=constants.SortingValues.ASC,
            filters=frontend_models.Filters(lte="2023-01-01", gte="2022-01-01"),
        ),
    ]
