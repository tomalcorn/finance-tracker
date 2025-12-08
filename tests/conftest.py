"""Helper functions and fixtures for tests."""

import os
import pathlib
import typing

import dotenv
import pytest
import st_supabase_connection
import streamlit as st
import streamlit.testing.v1 as st_test

from libs import backend_models, constants, frontend_models


@pytest.fixture(name="setup_test_env", scope="session", autouse=True)
def _setup_test_env() -> typing.Generator[None, None, None]:
    """Set up test environment variables for all tests."""
    # Store original values if they exist
    original_url = os.environ.get("SUPABASE_URL")
    original_key = os.environ.get("SUPABASE_KEY")
    # Set test values. Only load .env.test if it exists and variables are not already set
    env_file = pathlib.Path(__file__).parent.parent / ".env.test"
    if (
        "SUPABASE_URL" not in os.environ or "SUPABASE_KEY" not in os.environ
    ) and env_file.exists():
        dotenv.load_dotenv(env_file, override=False)

    os.environ.setdefault(
        "SUPABASE_URL",
        os.getenv("SUPABASE_URL", "http://localhost:54321"),
    )
    os.environ.setdefault("SUPABASE_KEY", os.getenv("SUPABASE_KEY", "test-anon-key"))

    yield

    # Restore original values or remove if they didn't exist
    if original_url is not None:
        os.environ["SUPABASE_URL"] = original_url
    elif "SUPABASE_URL" in os.environ:
        del os.environ["SUPABASE_URL"]

    if original_key is not None:
        os.environ["SUPABASE_KEY"] = original_key
    elif "SUPABASE_KEY" in os.environ:
        del os.environ["SUPABASE_KEY"]


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "supabase",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="yield_sample_user")
def _yield_sample_user(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[backend_models.UserModel, None, None]:
    """Set up a sample user for tests."""
    sample_user = backend_models.UserModel(first_name="Test", last_name="User")
    # Insert user into the test database
    connection.table("users").insert(sample_user.model_dump_json()).execute()

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
