"""Fixtures for the integration suite, which hits the live "testing" database.

Everything that touches Supabase lives here rather than in the root conftest, so
``pytest tests/unit`` needs no backend at all. The stale-row sweep used to sit up
there as an autouse fixture, which meant a unit-test-only run reached out and
emptied a shared table.

Every row these fixtures write belongs to ``run_scope.TEST_USER_ID``, which is
derived per run, and every delete they make is scoped to a specific id. Nothing
here empties a table.
"""

import typing
import uuid

import pytest
import st_supabase_connection
import streamlit as st
from tests import run_scope

from domain import entities


@pytest.fixture(autouse=True, scope="session")
def _sweep_stale_test_rows() -> None:
    """Remove rows left behind by test runs that are long finished.

    Doubly scoped, and that is the whole point (#221). Only rows whose ``user_id``
    carries ``run_scope.TEST_USER_PREFIX`` are candidates, and only those older
    than ``run_scope.stale_cutoff()`` — so a run happening *right now*, in CI or
    on someone's machine, can never have its rows pulled out from under it.

    Its predecessor emptied ``bank_accounts`` outright once per test module, which
    is what made concurrent runs fail: one run's wipe landed between another's
    "insert bank account" and "insert payment referencing it", and the payment hit
    a foreign-key violation.
    """
    connection: st_supabase_connection.SupabaseConnection = st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )
    cutoff = run_scope.stale_cutoff()
    for table in run_scope.SWEEP_TABLES:
        connection.table(table).delete().like(
            "user_id",
            f"{run_scope.TEST_USER_PREFIX}%",
        ).lt("_created_at", cutoff).execute()


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="sample_bank_account")
def _sample_bank_account() -> entities.BankAccountModel:
    """Provide a sample bank account model for tests."""
    return entities.BankAccountModel(
        user_id=run_scope.TEST_USER_ID,
        name="Test Account 1",
        starting_balance=100.0,
    )


@pytest.fixture(name="yield_sample_bank_account")
def _yield_sample_bank_account(
    connection: st_supabase_connection.SupabaseConnection,
    sample_bank_account: entities.BankAccountModel,
) -> typing.Generator[entities.BankAccountModel, None, None]:
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
    sample_bank_account: entities.BankAccountModel,
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[list[entities.BankAccountModel], None, None]:
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
