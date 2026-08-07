"""Fixtures for the integration suite, which hits the live "testing" database.

Everything that touches Supabase lives here rather than in the root conftest, so
``pytest tests/unit`` needs no backend at all. The stale-row sweep used to sit up
there as an autouse fixture, which meant a unit-test-only run reached out and
emptied a shared table.

Every integration test used to share one fixed identity, and the teardown emptied
whole tables, so two runs overlapping in time corrupted each other (#221). Now
``test_user_id`` is derived per run and nothing here empties a table: each delete
names an id, or is bounded by both the test-identity prefix and an age cutoff.
"""

import datetime
import os
import typing
import uuid

import pytest
import st_supabase_connection
import streamlit as st

from domain import entities

_TEST_USER_PREFIX = "auth0|test-"
"""Marks a user_id as belonging to a test run, so the sweep can find them."""

_STALE_AFTER = datetime.timedelta(hours=1)
"""How old a test row must be before the sweep will delete it.

Comfortably longer than a run (CI takes minutes) and comfortably shorter than
"forever", so leftovers do not accumulate in the shared project.
"""

_SWEEP_TABLES = (
    "payments",
    "subscriptions",
    "quick_buttons",
    "bank_accounts",
    "joint_account_members",
)
"""Tables the sweep empties of stale test rows, in foreign-key-safe order.

``payments.bank_account_id`` and ``subscriptions.bank_account_id`` are plain
references with no ``ON DELETE`` action, so the children have to go first or the
delete is rejected.
"""


@pytest.fixture(scope="session", name="test_user_id")
def _test_user_id() -> str:
    """Return the ``user_id`` every row this run writes belongs to.

    Session-scoped so every test in the run agrees on it — the fixtures and the
    teardowns have to scope themselves to the same user. In CI it is derived from
    the run, so a re-run gets its own; off CI it is random, so two local runs, or
    a local run beside a CI one, still cannot collide.
    """
    run_id = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    token = f"ci-{run_id}-{attempt}" if run_id else f"local-{uuid.uuid4().hex[:12]}"
    return f"{_TEST_USER_PREFIX}{token}"


@pytest.fixture(autouse=True, scope="session")
def _sweep_stale_test_rows() -> None:
    """Remove rows left behind by test runs that are long finished.

    Doubly scoped, and that is the whole point (#221). Only rows whose ``user_id``
    carries ``_TEST_USER_PREFIX`` are candidates, and only those older than
    ``_STALE_AFTER`` — so a run happening *right now*, in CI or on someone's
    machine, can never have its rows pulled out from under it.

    Its predecessor emptied ``bank_accounts`` outright once per test module, which
    is what made concurrent runs fail: one run's wipe landed between another's
    "insert bank account" and "insert payment referencing it", and the payment hit
    a foreign-key violation.
    """
    connection: st_supabase_connection.SupabaseConnection = st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )
    cutoff = (datetime.datetime.now(tz=datetime.UTC) - _STALE_AFTER).isoformat()
    for table in _SWEEP_TABLES:
        connection.table(table).delete().like(
            "user_id",
            f"{_TEST_USER_PREFIX}%",
        ).lt("_created_at", cutoff).execute()


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="sample_bank_account")
def _sample_bank_account(test_user_id: str) -> entities.BankAccountModel:
    """Provide a sample bank account model for tests."""
    return entities.BankAccountModel(
        user_id=test_user_id,
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
