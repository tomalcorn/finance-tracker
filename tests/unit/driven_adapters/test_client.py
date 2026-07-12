"""Unit tests for the Supabase client's error translation.

The Supabase connection is the external I/O boundary, so it is mocked here (as
in the repository tests) to drive a transport failure through the client's
public functions.
"""

from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest

from domain import entities
from driven_adapters import errors
from driven_adapters.supabase import client

if TYPE_CHECKING:
    import st_supabase_connection


def _connection(
    mock_conn: mock.MagicMock,
) -> "st_supabase_connection.SupabaseConnection":
    """Cast a bare mock to the connection type (its attrs are set dynamically)."""
    return cast("st_supabase_connection.SupabaseConnection", mock_conn)


def test_fetch_table_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    mock_conn.table.return_value.select.return_value.execute.side_effect = boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.fetch_table("bank_accounts", "*", _connection(mock_conn))

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom


def test_update_backend_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    mock_conn.table.return_value.insert.return_value.execute.side_effect = boom
    updates = entities.BackendUpdates(added_rows=[{"id": "x"}])

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.update_backend("bank_accounts", updates, _connection(mock_conn))

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom


def test_upsert_row_writes_through_the_upsert_endpoint() -> None:
    # Arrange
    mock_conn = mock.MagicMock()
    row: entities.JsonDict = {"id": "x", "name": "New"}

    # Act
    client.upsert_row("bank_accounts", row, _connection(mock_conn))

    # Assert - insert-or-update semantics, so the write must not go through insert
    mock_conn.table.return_value.upsert.assert_called_once_with(row)


def test_upsert_row_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    mock_conn.table.return_value.upsert.return_value.execute.side_effect = boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.upsert_row("bank_accounts", {"id": "x"}, _connection(mock_conn))

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom
