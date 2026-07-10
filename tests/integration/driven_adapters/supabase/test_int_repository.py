"""Integration tests for the Supabase repository CRUD path against the test DB.

Exercises the repository read (``get_all`` / ``get_by_ids``) and write
(``apply`` — add / edit / delete) path against the live "testing" connection.
Cache read-through and version invalidation are covered separately as unit
tests in ``tests/unit/composition/test_cache.py``.
"""

import uuid

import pytest
import st_supabase_connection

from composition import cache as composition_cache
from domain import entities, read_models
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

_USER_ID = "auth0|test-user-1"

type BankRepo = supabase_repos.SupabaseRepository[
    entities.BankAccountModel,
    read_models.BankAccountView,
]


@pytest.fixture(name="bank_repo")
def _bank_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> BankRepo:
    """Return a bank repository wired to the test connection and seed user."""
    return supabase_repos.bank_account_repository(
        _USER_ID,
        composition_cache.make_cache_gateway(connection),
    )


def _get_by_id(
    repo: BankRepo,
    account_id: uuid.UUID,
) -> entities.BankAccountModel | None:
    """Read a single account by ID via the surviving get_by_ids surface."""
    matches = repo.get_by_ids([account_id])
    return matches[0] if matches else None


class TestBankAccountRepositoryReads:
    """Reads through the repository (successor to data_client.get_data)."""

    def test_get_all_returns_seeded_account(
        self,
        bank_repo: BankRepo,
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
    """apply add / edit / delete (successor to data_client.update_backend)."""

    def test_apply_adds_row(
        self,
        bank_repo: BankRepo,
        connection: st_supabase_connection.SupabaseConnection,
        sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """A row added via apply is then readable."""
        # Arrange
        new_account = sample_bank_account.model_copy(
            update={"id": uuid.uuid4(), "name": "Added Account"},
            deep=True,
        )

        # Act
        cache._get_data_cached.clear()
        bank_repo.apply(
            entities.BackendUpdates(added_rows=[new_account.model_dump(mode="json")]),
        )
        cache._get_data_cached.clear()
        added = _get_by_id(bank_repo, new_account.id)

        # Clean up
        connection.table("bank_accounts").delete().eq(
            "id",
            str(new_account.id),
        ).execute()
        cache._get_data_cached.clear()

        # Assert
        added_as_expected = added is not None and added.name == "Added Account"
        assert added_as_expected

    def test_apply_edits_row(
        self,
        bank_repo: BankRepo,
        yield_sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """An edit applied via apply is reflected on the next read."""
        # Act
        cache._get_data_cached.clear()
        bank_repo.apply(
            entities.BackendUpdates(
                edited_rows={str(yield_sample_bank_account.id): {"name": "EditedName"}},
            ),
        )
        cache._get_data_cached.clear()
        edited = _get_by_id(bank_repo, yield_sample_bank_account.id)

        # Assert
        edited_as_expected = edited is not None and edited.name == "EditedName"
        assert edited_as_expected

    def test_apply_deletes_row(
        self,
        bank_repo: BankRepo,
        yield_sample_bank_account: entities.BankAccountModel,
    ) -> None:
        """A row deleted via apply is gone on the next read."""
        # Act
        cache._get_data_cached.clear()
        bank_repo.apply(
            entities.BackendUpdates(
                deleted_rows=[str(yield_sample_bank_account.id)],
            ),
        )
        cache._get_data_cached.clear()

        # Assert
        assert _get_by_id(bank_repo, yield_sample_bank_account.id) is None

    def test_apply_adds_edits_and_deletes(
        self,
        bank_repo: BankRepo,
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
        bank_repo.apply(
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
