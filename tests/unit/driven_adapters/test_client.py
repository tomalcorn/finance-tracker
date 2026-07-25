"""Unit tests for the Supabase client's error translation.

The Supabase connection is the external I/O boundary, so it is mocked here (as
in the repository tests) to drive a transport failure through the client's
public functions.
"""

from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest

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


def test_upsert_rows_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    mock_conn.table.return_value.upsert.return_value.execute.side_effect = boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.upsert_rows("bank_accounts", [{"id": "x"}], _connection(mock_conn))

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom


def test_update_rows_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    table = mock_conn.table.return_value
    table.update.return_value.eq.return_value.execute.side_effect = boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.update_rows(
            "bank_accounts",
            {"x": {"name": "n"}},
            _connection(mock_conn),
        )

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom


def test_delete_rows_translates_a_transport_failure() -> None:
    # Arrange
    boom = ConnectionError("network down")
    mock_conn = mock.MagicMock()
    table = mock_conn.table.return_value
    table.delete.return_value.in_.return_value.execute.side_effect = boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.delete_rows("bank_accounts", ["x"], _connection(mock_conn))

    # Assert - the transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom
