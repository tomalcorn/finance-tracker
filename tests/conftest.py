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


@pytest.fixture(name="sample_bank_account")
def _sample_bank_account() -> backend_models.BankAccountModel:
    """Provide a sample bank account model for tests."""
    return backend_models.BankAccountModel(
        user_id="auth0|test-user-1",
        name="Test Account 1",
        starting_balance=100.0,
    )


@pytest.fixture(name="yield_sample_bank_account")
def _yield_sample_bank_account(
    connection: st_supabase_connection.SupabaseConnection,
    sample_bank_account: backend_models.BankAccountModel,
) -> typing.Generator[backend_models.BankAccountModel, None, None]:
    """Set up a sample bank account for tests."""
    connection.table("bank_accounts").insert(
        sample_bank_account.model_dump(mode="json"),
    ).execute()

    yield sample_bank_account

    # Clean up the bank account from the test database
    connection.table("bank_accounts").delete().eq(
        "id",
        str(sample_bank_account.id),
    ).execute()


@pytest.fixture(name="yield_sample_bank_accounts")
def _yield_sample_bank_accounts(
    sample_bank_account: backend_models.BankAccountModel,
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[list[backend_models.BankAccountModel], None, None]:
    """Set up multiple sample bank accounts for tests."""
    sample_bank_accounts = [
        sample_bank_account,
        sample_bank_account.model_copy(
            update={"id": uuid.uuid4(), "name": "Test Account 2"},
            deep=True,
        ),
    ]
    # Insert bank accounts into the test database
    for account in sample_bank_accounts:
        connection.table("bank_accounts").insert(
            account.model_dump(mode="json"),
        ).execute()

    yield sample_bank_accounts

    # Clean up the bank accounts from the test database
    for account in sample_bank_accounts:
        connection.table("bank_accounts").delete().eq(
            "id",
            str(account.id),
        ).execute()


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
