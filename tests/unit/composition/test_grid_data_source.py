"""Unit tests for the composition-layer RepositoryGridDataSource."""

import uuid

import pytest

from composition import grid_data_source
from domain import read_models


class _StubRepository:
    """Stub repository returning fixed raw view rows and column values."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        column_values: set[object] | None = None,
    ) -> None:
        self._rows = rows or []
        self._column_values = column_values or set()

    def get_rows(self) -> list[dict]:
        return self._rows

    def get_column_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return self._column_values


def _budget_tracker_row() -> dict:
    """Return a raw budget_tracker_view row with all computed columns."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": "auth0|abc",
        "name": "Expenses",
        "total_budget": 1000.0,
        "current_month": 250.0,
        "remaining": 750.0,
        "progress": 25.0,
        "split": 40.0,
    }


def test_rows_maps_raw_rows_to_view_models() -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[_budget_tracker_row()]),
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    rows = source.rows()

    # Assert
    assert all(isinstance(row, read_models.BudgetTrackerView) for row in rows)


def test_rows_preserves_computed_columns() -> None:
    # Arrange
    raw = _budget_tracker_row()
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[raw]),
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    dumped = source.rows()[0].model_dump()

    # Assert
    assert all(
        [
            dumped["current_month"] == raw["current_month"],
            dumped["remaining"] == raw["remaining"],
            dumped["progress"] == raw["progress"],
            dumped["split"] == raw["split"],
        ],
    )


def test_rows_without_view_model_raises() -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[_budget_tracker_row()]),
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="no view model"):
        source.rows()


def test_unique_values_delegates_to_repository() -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(column_values={"Expenses", "Savings"}),
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    values = source.unique_values("name")

    # Assert
    assert values == {"Expenses", "Savings"}
