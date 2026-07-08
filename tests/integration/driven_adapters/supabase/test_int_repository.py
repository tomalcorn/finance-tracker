"""Integration tests for the Supabase repository CRUD path against the test DB.

Successor to the deleted ``test_int_data_client`` suite: it exercises the
repository read (``get_all`` / ``get_by_id``) and write (``apply_updates`` —
add / edit / delete) path — the code that replaced ``ui.data_client`` — against
the live "testing" connection. Cache read-through and version invalidation are
covered separately as unit tests in ``tests/unit/composition/test_cache.py``.
"""

import uuid

import pytest
import st_supabase_connection
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

from domain import entities

_USER_ID = "auth0|test-user-1"


@pytest.fixture(name="bank_repo")
def _bank_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> supabase_repos.SupabaseBankAccountRepository:
    """Return a bank repository bound to the test connection and seed user."""
    return supabase_repos.SupabaseBankAccountRepository(connection, _USER_ID)


class TestBankAccountRepositoryReads:
    """Reads through the repository (successor to data_client.get_data)."""

    def test_get_all_returns_seeded_account(
        self,
        bank_repo: supabase_repos.SupabaseBankAccountRepository,
        yield_sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """get_all returns the user's seeded account."""
        # Arrange
        cache._get_data_cached.clear()

        # Act
        account_ids = {account.id for account in bank_repo.get_all()}

        # Assert
        assert yield_sample_bank_account.id in account_ids


class TestBankAccountRepositoryWrites:
    """apply_updates add / edit / delete (successor to data_client.update_backend)."""

    def test_apply_updates_adds_row(
        self,
        bank_repo: supabase_repos.SupabaseBankAccountRepository,
        connection: st_supabase_connection.SupabaseConnection,
        sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """A row added via apply_updates is then readable."""
        # Arrange
        new_account = sample_bank_account.model_copy(
            update={"id": uuid.uuid4(), "name": "Added Account"},
            deep=True,
        )

        # Act
        cache._get_data_cached.clear()
        bank_repo.apply_updates(
            entities.BackendUpdates(added_rows=[new_account.model_dump(mode="json")]),
        )
        cache._get_data_cached.clear()
        added = bank_repo.get_by_id(new_account.id)

        # Clean up
        connection.table("bank_accounts").delete().eq(
            "id",
            str(new_account.id),
        ).execute()
        cache._get_data_cached.clear()

        # Assert
        added_as_expected = added is not None and added.name == "Added Account"
        assert added_as_expected

    def test_apply_updates_edits_row(
        self,
        bank_repo: supabase_repos.SupabaseBankAccountRepository,
        yield_sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """An edit applied via apply_updates is reflected on the next read."""
        # Act
        cache._get_data_cached.clear()
        bank_repo.apply_updates(
            entities.BackendUpdates(
                edited_rows={str(yield_sample_bank_account.id): {"name": "EditedName"}},
            ),
        )
        cache._get_data_cached.clear()
        edited = bank_repo.get_by_id(yield_sample_bank_account.id)

        # Assert
        edited_as_expected = edited is not None and edited.name == "EditedName"
        assert edited_as_expected

    def test_apply_updates_deletes_row(
        self,
        bank_repo: supabase_repos.SupabaseBankAccountRepository,
        yield_sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """A row deleted via apply_updates is gone on the next read."""
        # Act
        cache._get_data_cached.clear()
        bank_repo.apply_updates(
            entities.BackendUpdates(
                deleted_rows=[str(yield_sample_bank_account.id)],
            ),
        )
        cache._get_data_cached.clear()

        # Assert
        assert bank_repo.get_by_id(yield_sample_bank_account.id) is None

    def test_apply_updates_adds_edits_and_deletes(
        self,
        bank_repo: supabase_repos.SupabaseBankAccountRepository,
        connection: st_supabase_connection.SupabaseConnection,
        sample_bank_account: entities.BankAccountModel,
        yield_sample_bank_accounts: list[entities.BankAccountModel],
    ) -> None:
        """A single batch of add + edit + delete is applied atomically."""
        # Arrange
        new_account = sample_bank_account.model_copy(
            update={"id": uuid.uuid4(), "name": "Added Combined"},
            deep=True,
        )

        # Act
        cache._get_data_cached.clear()
        bank_repo.apply_updates(
            entities.BackendUpdates(
                added_rows=[new_account.model_dump(mode="json")],
                edited_rows={
                    str(yield_sample_bank_accounts[0].id): {"name": "EditedCombined"},
                },
                deleted_rows=[str(yield_sample_bank_accounts[1].id)],
            ),
        )
        cache._get_data_cached.clear()
        accounts = {account.id: account for account in bank_repo.get_all()}

        # Clean up the added row (the fixture only tracks the seeded ones)
        connection.table("bank_accounts").delete().eq(
            "id",
            str(new_account.id),
        ).execute()
        cache._get_data_cached.clear()

        # Assert
        added_present = new_account.id in accounts
        edited = accounts.get(yield_sample_bank_accounts[0].id)
        edited_applied = edited is not None and edited.name == "EditedCombined"
        deleted_absent = yield_sample_bank_accounts[1].id not in accounts
        assert all([added_present, edited_applied, deleted_absent])
