"""Unit tests for the composition-layer StreamlitCacheGateway."""

from unittest import mock

import pytest
import st_supabase_connection

from composition import cache as composition_cache
from domain import entities
from driven_adapters.supabase import table_names
from driving_adapters import cache as ui_cache

_PAYMENTS = str(table_names.TableNames.PAYMENTS)


@pytest.fixture(name="mock_connection")
def _mock_connection() -> mock.MagicMock:
    return mock.MagicMock(spec=st_supabase_connection.SupabaseConnection)


@pytest.fixture(name="gateway")
def _gateway(
    mock_connection: mock.MagicMock,
) -> composition_cache.StreamlitCacheGateway:
    return composition_cache.make_cache_gateway(mock_connection)


def _affected_keys() -> set[str]:
    """Return the table plus every view a payments write should invalidate."""
    views = table_names.VIEWS_AFFECTED_BY[table_names.TableNames.PAYMENTS]
    return {_PAYMENTS, *(str(v) for v in views)}


class TestWrite:
    """Tests for StreamlitCacheGateway.write."""

    def test_persists_updates_to_the_client(
        self,
        gateway: composition_cache.StreamlitCacheGateway,
        mock_connection: mock.MagicMock,
    ) -> None:
        # Arrange
        updates = entities.BackendUpdates(added_rows=[{"id": "1"}])

        # Act
        with mock.patch.object(
            composition_cache.client,
            "update_backend",
        ) as mock_update:
            gateway.write(_PAYMENTS, updates)

        # Assert
        mock_update.assert_called_once_with(_PAYMENTS, updates, mock_connection)

    def test_bumps_version_for_table_and_affected_views(
        self,
        gateway: composition_cache.StreamlitCacheGateway,
    ) -> None:
        # Arrange
        updates = entities.BackendUpdates(added_rows=[{"id": "1"}])

        # Act
        with mock.patch.object(composition_cache.client, "update_backend"):
            gateway.write(_PAYMENTS, updates)

        # Assert - every affected key is bumped from 0 to 1, and nothing else
        versions = ui_cache._get_table_versions()
        expected = _affected_keys()
        assert all(
            [
                set(versions) == expected,
                all(versions[key] == 1 for key in expected),
            ],
        )

    def test_invalidation_is_skipped_when_there_are_no_changes(
        self,
        gateway: composition_cache.StreamlitCacheGateway,
    ) -> None:
        # Act - an empty BackendUpdates still persists (a no-op) but must not
        # bump any cache versions.
        with mock.patch.object(composition_cache.client, "update_backend"):
            gateway.write(_PAYMENTS, entities.BackendUpdates())

        # Assert
        assert ui_cache._get_table_versions() == {}


class TestFetch:
    """Tests for StreamlitCacheGateway.fetch."""

    def test_reads_through_the_shared_versioned_cache(
        self,
        gateway: composition_cache.StreamlitCacheGateway,
        mock_connection: mock.MagicMock,
    ) -> None:
        # Arrange
        rows = [{"id": "1"}]

        # Act
        with mock.patch.object(
            composition_cache.ui_cache,
            "fetch",
            return_value=rows,
        ) as mock_fetch:
            result = gateway.fetch(_PAYMENTS)

        # Assert - full-table read through the versioned cache
        assert result == rows
        mock_fetch.assert_called_once_with(_PAYMENTS, "*", mock_connection)
