"""Integration tests for data_client module."""

import st_supabase_connection
from ui import data_client

from domain import entities


class TestGetData:
    """Integration tests for data_client.get_data."""

    def test_get_data(
        self,
        yield_sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching data using sample bank account."""
        # Act
        data = data_client.get_data("bank_accounts", "*", _connection=connection)

        # Assert
        expected_model = yield_sample_bank_account
        actual_model = entities.BankAccountModel.model_validate(data[0])
        # Clear up cache
        data_client._get_data_cached.clear()
        assert actual_model == expected_model

    def test_get_data_caching(
        self,
        yield_sample_bank_account: entities.BankAccountModel,  # noqa: ARG002
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that repeated identical get_data calls use the cache."""
        from unittest import mock

        # Arrange
        data_client._get_data_cached.clear()

        # Act
        with mock.patch.object(
            data_client,
            "_execute_query",
            wraps=data_client._execute_query,
        ) as mock_execute:
            data_client.get_data("bank_accounts", "*", _connection=connection)
            data_client.get_data("bank_accounts", "*", _connection=connection)

        # Clean up
        data_client._get_data_cached.clear()

        # Assert - two identical calls should produce exactly one DB round trip
        assert mock_execute.call_count == 1


class TestGetColumnValues:
    """Integration tests for data_client.get_column_values."""

    def test_get_column_values(
        self,
        yield_sample_bank_accounts: list[entities.BankAccountModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching distinct column values using sample bank accounts."""
        # Act
        column_values = data_client.get_column_values(
            table_name="bank_accounts",
            column_name="name",
            connection=connection,
        ).to_list()

        # Assert
        expected_names = [account.name for account in yield_sample_bank_accounts]
        assert column_values == expected_names

    def test_get_column_values_unique(
        self,
        yield_sample_bank_accounts: list[entities.BankAccountModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching unique column values using sample bank accounts."""
        # Act
        column_values = data_client.get_column_values(
            table_name="bank_accounts",
            column_name="user_id",
            connection=connection,
            unique=True,
        )

        # Assert
        expected_user_ids = {account.user_id for account in yield_sample_bank_accounts}
        assert set(column_values) == expected_user_ids


class TestUpdateBackend:
    """Integration tests for data_client.update_backend."""

    def test_adds_new_row(
        self,
        sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test adding a new row to the backend."""
        # Arrange
        updates = entities.BackendUpdates(
            added_rows=[sample_bank_account.model_dump(mode="json")],
        )

        # Act
        data_client.update_backend(
            table_name="bank_accounts",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="bank_accounts",
            query_string="*",
            _connection=connection,
        )
        actual_model = entities.BankAccountModel.model_validate(fetched_data[0])
        # Clean up
        data_client._get_data_cached.clear()
        connection.table("bank_accounts").delete().eq(
            "id",
            str(actual_model.id),
        ).execute()
        assert actual_model == sample_bank_account

    def test_deletes_row(
        self,
        yield_sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test deleting a row from the backend."""
        # Arrange
        updates = entities.BackendUpdates(
            deleted_rows=[str(yield_sample_bank_account.id)],
        )

        # Act
        data_client.update_backend(
            table_name="bank_accounts",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="bank_accounts",
            query_string="*",
            _connection=connection,
        )

        # Clean up cache
        data_client._get_data_cached.clear()
        assert all(
            entities.BankAccountModel.model_validate(row).id
            != yield_sample_bank_account.id
            for row in fetched_data
        )

    def test_edits_row(
        self,
        yield_sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test editing a row in the backend."""
        # Arrange
        new_name = "UpdatedName"
        updates = entities.BackendUpdates(
            edited_rows={
                str(yield_sample_bank_account.id): {"name": new_name},
            },
        )

        # Act
        data_client.update_backend(
            table_name="bank_accounts",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="bank_accounts",
            query_string="*",
            _connection=connection,
        )

        # Clean up cache
        data_client._get_data_cached.clear()

        # Find the updated bank account and check the name
        for row in fetched_data:
            account = entities.BankAccountModel.model_validate(row)
            if account.id == yield_sample_bank_account.id:
                updated_account = account
                break
        assert updated_account.name == new_name

    def test_adds_and_edits_and_deletes_rows(
        self,
        yield_sample_bank_accounts: list[entities.BankAccountModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test adding, editing and deleting a row in the backend."""
        # Arrange - Add a new account, then edit one of the existing accounts
        new_account = entities.BankAccountModel(
            user_id="auth0|int-test-new-user",
            name="New Account",
        )
        updates = entities.BackendUpdates(
            added_rows=[new_account.model_dump(mode="json")],
            edited_rows={
                str(yield_sample_bank_accounts[0].id): {"name": "EditedName"},
            },
            # Delete the second account
            deleted_rows=[str(yield_sample_bank_accounts[1].id)],
        )

        # Act
        data_client.update_backend(
            table_name="bank_accounts",
            updates=updates,
            connection=connection,
        )

        # Assert and clean up
        fetched_data = data_client.get_data(
            table_name="bank_accounts",
            query_string="*",
            _connection=connection,
        )
        # Check new account added
        added_account_found = any(
            entities.BankAccountModel.model_validate(row).id == new_account.id
            for row in fetched_data
        )
        # Check existing account edited
        edited_account_edited = False
        for row in fetched_data:
            account = entities.BankAccountModel.model_validate(row)
            edited = (
                account.id == yield_sample_bank_accounts[0].id
                and account.name == "EditedName"
            )
            if edited:
                edited_account_edited = True
                break
        # Check deleted account is gone
        deleted_account_not_found = all(
            entities.BankAccountModel.model_validate(row).id
            != yield_sample_bank_accounts[1].id
            for row in fetched_data
        )
        # Clean up added account and cache
        connection.table("bank_accounts").delete().eq(
            "id",
            str(new_account.id),
        ).execute()
        data_client._get_data_cached.clear()

        assert all(
            [
                added_account_found,
                edited_account_edited,
                deleted_account_not_found,
            ],
        )

    def test_clears_cache_for_table(
        self,
        yield_sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that update_backend clears the get_data cache for the updated table."""
        # Arrange - record the current version
        data_client._get_data_cached.clear()
        version_before = data_client._get_table_versions().get("bank_accounts", 0)

        # Act
        updates = entities.BackendUpdates(
            edited_rows={
                str(yield_sample_bank_account.id): {"name": "UpdatedForCacheTest"},
            },
        )
        data_client.update_backend(
            "bank_accounts",
            updates=updates,
            connection=connection,
        )
        version_after = data_client._get_table_versions().get("bank_accounts", 0)

        # Assert - version should have been bumped, invalidating all cached results
        assert version_after == version_before + 1

    def test_updates_backend_updates_model(
        self,
        yield_sample_bank_account: entities.BankAccountModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that BackendUpdates model is updated correctly after backend update."""
        # Arrange
        updates = entities.BackendUpdates(
            deleted_rows=[str(yield_sample_bank_account.id)],
        )

        # Act
        updated_updates = data_client.update_backend(
            table_name="bank_accounts",
            updates=updates,
            connection=connection,
        )

        # Assert
        assert all(
            [
                updated_updates.deleted_rows is not None,
                len(updated_updates.deleted_rows)
                == 0,  # deleted_rows list should be cleared after processing
            ],
        )
