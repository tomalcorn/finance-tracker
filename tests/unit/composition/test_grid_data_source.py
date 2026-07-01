"""Unit tests for the composition-layer RepositoryGridDataSource."""

import uuid

import pytest

from composition import grid_data_source
from domain import entities, read_models


@pytest.fixture(name="budget_tracker_row")
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


class _StubRepository:
    """Stub repository recording writes and returning fixed reads."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        column_values: set[object] | None = None,
    ) -> None:
        self._rows = rows or []
        self._column_values = column_values or set()
        self.applied: list[entities.BackendUpdates] = []

    def get_rows(self) -> list[dict]:
        return self._rows

    def get_column_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return self._column_values

    def apply_updates(self, updates: entities.BackendUpdates) -> None:
        self.applied.append(updates)


def test_rows_maps_raw_rows_to_view_models(budget_tracker_row: dict) -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[budget_tracker_row]),
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    rows = source.rows()

    # Assert
    assert all(isinstance(row, read_models.BudgetTrackerView) for row in rows)


def test_rows_preserves_computed_columns(budget_tracker_row: dict) -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[budget_tracker_row]),
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    dumped = source.rows()[0].model_dump()

    # Assert
    assert all(
        [
            dumped["current_month"] == budget_tracker_row["current_month"],
            dumped["remaining"] == budget_tracker_row["remaining"],
            dumped["progress"] == budget_tracker_row["progress"],
            dumped["split"] == budget_tracker_row["split"],
        ],
    )


def test_rows_without_view_model_raises(budget_tracker_row: dict) -> None:
    # Arrange
    source = grid_data_source.RepositoryGridDataSource(
        _StubRepository(rows=[budget_tracker_row]),
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


@pytest.fixture(name="changes")
def _changes() -> entities.BackendUpdates:
    """Return a BackendUpdates batch with an add, an edit, and a delete."""
    return entities.BackendUpdates(
        added_rows=[{"name": "New"}],
        edited_rows={str(uuid.uuid4()): {"name": "Renamed"}},
        deleted_rows=[str(uuid.uuid4())],
    )


def test_apply_delegates_batch_to_repository(
    changes: entities.BackendUpdates,
) -> None:
    # Arrange
    repository = _StubRepository()
    source = grid_data_source.RepositoryGridDataSource(
        repository,
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    source.apply(changes)

    # Assert
    assert repository.applied == [changes]


def test_apply_forwards_empty_batch() -> None:
    # Arrange
    repository = _StubRepository()
    source = grid_data_source.RepositoryGridDataSource(
        repository,
        view_model=read_models.BudgetTrackerView,
    )

    # Act
    source.apply(entities.BackendUpdates())

    # Assert
    assert repository.applied == [entities.BackendUpdates()]
