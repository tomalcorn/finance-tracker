"""Integration tests for data_client module."""

import st_supabase_connection

from apps import data_client
from libs.models import backend_models


class TestGetData:
    """Integration tests for data_client.get_data."""

    def test_get_data(
        self,
        yield_sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching data using sample user."""
        # Act
        data = data_client.get_data("users", "*", _connection=connection)

        # Assert
        expected_user_model = yield_sample_user
        actual_user_model = backend_models.UserModel.model_validate(data[0])
        # Clear up cache
        data_client.get_data.clear()
        assert actual_user_model == expected_user_model

    def test_get_data_caching(
        self,
        yield_sample_user: backend_models.UserModel,  # noqa: ARG002
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that repeated identical get_data calls use the cache."""
        # Arrange
        data_client.get_data.clear()

        # Act
        data_client.get_data("users", "*", _connection=connection)
        data_client.get_data("users", "*", _connection=connection)
        cache_size = len(data_client.get_data._cache)

        # Clean up
        data_client.get_data.clear()

        # Assert - two identical calls should produce exactly one cache entry
        assert cache_size == 1


class TestGetColumnValues:
    """Integration tests for data_client.get_column_values."""

    def test_get_column_values(
        self,
        yield_sample_users: list[backend_models.UserModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching distinct column values using sample users."""
        # Act
        column_values = data_client.get_column_values(
            table_name="users",
            column_name="last_name",
            connection=connection,
        ).to_list()

        # Assert
        expected_last_names = [user.last_name for user in yield_sample_users]
        assert column_values == expected_last_names

    def test_get_column_values_unique(
        self,
        yield_sample_users: list[backend_models.UserModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test fetching unique column values using sample users."""
        # Act
        column_values = data_client.get_column_values(
            table_name="users",
            column_name="first_name",
            connection=connection,
            unique=True,
        )

        # Assert
        expected_first_names = {user.first_name for user in yield_sample_users}
        assert set(column_values) == expected_first_names


class TestUpdateBackend:
    """Integration tests for data_client.update_backend."""

    def test_adds_new_row(
        self,
        sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test adding a new row to the backend."""
        # Arrange
        updates = backend_models.BackendUpdates(
            added_rows=[sample_user.model_dump(mode="json")],
        )

        # Act
        data_client.update_backend(
            table_name="users",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="users",
            query_string="*",
            _connection=connection,
        )
        actual_user_model = backend_models.UserModel.model_validate(fetched_data[0])
        # Clean up
        data_client.get_data.clear()
        connection.table("users").delete().eq("id", actual_user_model.id).execute()
        assert actual_user_model == sample_user

    def test_deletes_row(
        self,
        yield_sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test deleting a row from the backend."""
        # Arrange
        updates = backend_models.BackendUpdates(
            deleted_rows=[str(yield_sample_user.id)],
        )

        # Act
        data_client.update_backend(
            table_name="users",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="users",
            query_string="*",
            _connection=connection,
        )

        # Clean up cache
        data_client.get_data.clear()
        assert all(
            backend_models.UserModel.model_validate(row).id != yield_sample_user.id
            for row in fetched_data
        )

    def test_edits_row(
        self,
        yield_sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test editing a row in the backend."""
        # Arrange
        new_first_name = "UpdatedName"
        updates = backend_models.BackendUpdates(
            edited_rows={
                str(yield_sample_user.id): {"first_name": new_first_name},
            },
        )

        # Act
        data_client.update_backend(
            table_name="users",
            updates=updates,
            connection=connection,
        )

        # Assert
        fetched_data = data_client.get_data(
            table_name="users",
            query_string="*",
            _connection=connection,
        )

        # Clean up cache
        data_client.get_data.clear()

        # Find the updated user and check the first name
        for row in fetched_data:
            user = backend_models.UserModel.model_validate(row)
            if user.id == yield_sample_user.id:
                updated_user = user
                break
        assert updated_user.first_name == new_first_name

    def test_adds_and_edits_and_deletes_rows(
        self,
        yield_sample_users: list[backend_models.UserModel],
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test adding, editing and deleting a row in the backend."""
        # Arrange - Add a new user, then edit one of the existing users
        new_user = backend_models.UserModel(
            first_name="New",
            last_name="User",
        )
        updates = backend_models.BackendUpdates(
            added_rows=[new_user.model_dump(mode="json")],
            edited_rows={
                str(yield_sample_users[0].id): {"last_name": "EditedLastName"},
            },
            deleted_rows=[str(yield_sample_users[1].id)],  # Delete the second user
        )

        # Act
        data_client.update_backend(
            table_name="users",
            updates=updates,
            connection=connection,
        )

        # Assert and clean up
        fetched_data = data_client.get_data(
            table_name="users",
            query_string="*",
            _connection=connection,
        )
        # Check new user added
        added_user_found = any(
            backend_models.UserModel.model_validate(row).id == new_user.id
            for row in fetched_data
        )
        # Check existing user edited
        edited_user_edited = False
        for row in fetched_data:
            user = backend_models.UserModel.model_validate(row)
            edited = (
                user.id == yield_sample_users[0].id
                and user.last_name == "EditedLastName"
            )
            if edited:
                edited_user_edited = True
                break
        # Check deleted user is gone
        deleted_user_not_found = all(
            backend_models.UserModel.model_validate(row).id != yield_sample_users[1].id
            for row in fetched_data
        )
        # Clean up added user and cache
        connection.table("users").delete().eq("id", new_user.id).execute()
        data_client.get_data.clear()

        assert all(
            [
                added_user_found,
                edited_user_edited,
                deleted_user_not_found,
            ],
        )

    def test_clears_cache_for_table(
        self,
        yield_sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that update_backend clears the get_data cache for the updated table."""
        # Arrange - populate the cache
        data_client.get_data.clear()
        data_client.get_data("users", "*", _connection=connection)
        cache_size_before = len(data_client.get_data._cache)

        # Act
        updates = backend_models.BackendUpdates(
            edited_rows={
                str(yield_sample_user.id): {"first_name": "UpdatedForCacheTest"},
            },
        )
        data_client.update_backend("users", updates=updates, connection=connection)
        cache_size_after = len(data_client.get_data._cache)

        # Assert
        assert all([cache_size_before == 1, cache_size_after == 0])

    def test_updates_backend_updates_model(
        self,
        yield_sample_user: backend_models.UserModel,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """Test that BackendUpdates model is updated correctly after backend update."""
        # Arrange
        updates = backend_models.BackendUpdates(
            deleted_rows=[str(yield_sample_user.id)],
        )

        # Act
        updated_updates = data_client.update_backend(
            table_name="users",
            updates=updates,
            connection=connection,
        )

        # Assert
        assert len(updated_updates.deleted_rows) == 0
