"""Unit tests for the Supabase client's paged reads and error translation.

Reads go through a stub connection that behaves like PostgREST: it caps every
response at ``max-rows`` and gives no stable order unless one is requested. The
write paths still drive a transport failure through a mocked connection.
"""

import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self, cast
from unittest import mock

import pytest

from driven_adapters import errors
from driven_adapters.supabase import client

if TYPE_CHECKING:
    import st_supabase_connection

    from domain import entities

_MAX_ROWS = 1000
"""Supabase's default PostgREST ``max-rows``: the most rows one response holds."""


class _StubResponse:
    """The ``data`` of an executed request."""

    def __init__(self, data: "list[entities.JsonDict]") -> None:
        self.data = data


class _StubSelect:
    """A select over one table's rows, applying the filters, order and range given.

    Without an order it returns the rows rotated by a different amount on each
    request, as Postgres guarantees no order, so unordered paging repeats and
    skips rows the way it can against a real table.
    """

    def __init__(
        self,
        connection: "_StubConnection",
        rows: "list[entities.JsonDict]",
    ) -> None:
        self._connection = connection
        self._rows = rows
        self._ordered = False
        self._range: tuple[int, int] | None = None

    def select(self, query_string: str) -> Self:  # noqa: ARG002 - always reads every column
        return self

    def eq(self, column: str, value: str) -> Self:
        self._rows = [row for row in self._rows if row[column] == value]
        return self

    def order(self, column: str) -> Self:
        self._rows = sorted(self._rows, key=lambda row: str(row[column]))
        self._ordered = True
        return self

    def range(self, start: int, end: int) -> Self:
        self._range = (start, end)
        return self

    def execute(self) -> _StubResponse:
        self._connection.requests += 1
        if self._connection.failure is not None:
            raise self._connection.failure
        rows = self._rows
        if not self._ordered and rows:
            shift = (self._connection.requests * 7) % len(rows)
            rows = rows[shift:] + rows[:shift]
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        return _StubResponse(rows[:_MAX_ROWS])


class _StubConnection:
    """Serves seeded tables, counting the requests made against them."""

    def __init__(
        self,
        tables: "dict[str, list[entities.JsonDict]]",
        failure: Exception | None = None,
    ) -> None:
        self._tables = tables
        self.failure = failure
        self.requests = 0

    def table(self, table_name: str) -> _StubSelect:
        return _StubSelect(self, self._tables[table_name])


@pytest.fixture(name="build_connection")
def _build_connection() -> Callable[..., Any]:
    """Return a builder for a stub connection, typed as the real one."""

    def build(
        tables: "dict[str, list[entities.JsonDict]] | None" = None,
        failure: Exception | None = None,
    ) -> "st_supabase_connection.SupabaseConnection":
        stub = _StubConnection(tables or {"payments": []}, failure)
        return cast("st_supabase_connection.SupabaseConnection", stub)

    return build


@pytest.fixture(name="build_rows")
def _build_rows() -> Callable[..., Any]:
    """Return a builder for ``count`` payment rows of one ownership type."""

    def build(
        count: int,
        ownership_type: str = "personal",
    ) -> "list[entities.JsonDict]":
        return [
            {"id": str(uuid.uuid4()), "ownership_type": ownership_type}
            for _ in range(count)
        ]

    return build


def _connection(
    mock_conn: mock.MagicMock,
) -> "st_supabase_connection.SupabaseConnection":
    """Cast a bare mock to the connection type (its attrs are set dynamically)."""
    return cast("st_supabase_connection.SupabaseConnection", mock_conn)


@pytest.mark.parametrize("count", [0, 1, 999, 1000, 1001, 2000, 2500])
def test_fetch_table_returns_every_row(
    count: int,
    build_connection: Callable[..., Any],
    build_rows: Callable[..., Any],
) -> None:
    # Arrange
    rows = build_rows(count)
    connection = build_connection({"payments": rows})

    # Act
    fetched = client.fetch_table("payments", "*", connection)

    # Assert - each row exactly once, however many pages it took
    assert sorted(row["id"] for row in fetched) == sorted(row["id"] for row in rows)


def test_fetch_table_applies_eq_filters_to_every_page(
    build_connection: Callable[..., Any],
    build_rows: Callable[..., Any],
) -> None:
    # Arrange
    joint = build_rows(1500, "joint")
    connection = build_connection({"payments": build_rows(1500) + joint})

    # Act
    fetched = client.fetch_table(
        "payments",
        "*",
        connection,
        {"ownership_type": "joint"},
    )

    # Assert
    assert sorted(row["id"] for row in fetched) == sorted(row["id"] for row in joint)


def test_fetch_table_reads_a_table_under_one_page_in_one_request(
    build_rows: Callable[..., Any],
) -> None:
    # Arrange
    stub = _StubConnection({"payments": build_rows(10)})

    # Act
    client.fetch_table(
        "payments",
        "*",
        cast("st_supabase_connection.SupabaseConnection", stub),
    )

    # Assert
    assert stub.requests == 1


def test_fetch_table_translates_a_transport_failure(
    build_connection: Callable[..., Any],
) -> None:
    # Arrange
    boom = ConnectionError("network down")
    connection = build_connection(failure=boom)

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client.fetch_table("payments", "*", connection)

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
