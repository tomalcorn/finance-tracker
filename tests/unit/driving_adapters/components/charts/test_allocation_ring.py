"""Unit tests for the allocation ring's segments and palette."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest

from domain import entities, read_models
from driving_adapters.components.charts import allocation_ring

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(name="build_root")
def _build_root() -> "Callable[..., read_models.CategoryView]":
    """Return a builder for a budget tracker row with a given budget."""

    def _build(
        name: entities.BudgetTrackerName = entities.BudgetTrackerName.EXPENSES,
        budget: float = 100.0,
    ) -> "read_models.CategoryView":
        return read_models.CategoryView.model_validate(
            {
                "id": uuid.uuid4(),
                "user_id": "auth0|test-user-1",
                "name": name,
                "parent_id": None,
                "budget": budget,
                "accrual": entities.AccrualPeriod.MONTHLY,
                "accrued": 0.0,
                "remaining": budget,
                "progress": 0.0,
                "split": 0.0,
                "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            },
        )

    return _build


def test_the_remainder_closes_the_ring_when_income_is_left_over(
    build_root: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange
    roots = [build_root(budget=300.0)]

    # Act
    segments = allocation_ring.slices(roots, income=500.0)

    # Assert - the remainder is what makes the ring the whole income
    assert segments[-1] == allocation_ring.Slice(
        allocation_ring.UNALLOCATED_LABEL,
        200.0,
    )


def test_no_remainder_segment_once_the_trackers_exceed_the_income(
    build_root: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - the ring is already full, so a remainder would have to be
    # negative; the shortfall is reported in the centre instead.
    roots = [build_root(budget=800.0)]

    # Act
    segments = allocation_ring.slices(roots, income=500.0)

    # Assert
    assert [segment.name for segment in segments] == [
        entities.BudgetTrackerName.EXPENSES,
    ]


def test_a_tracker_budgeted_at_nothing_gets_no_segment(
    build_root: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange
    roots = [
        build_root(name=entities.BudgetTrackerName.EXPENSES, budget=300.0),
        build_root(name=entities.BudgetTrackerName.SAVINGS, budget=0.0),
    ]

    # Act
    segments = allocation_ring.slices(roots, income=300.0)

    # Assert
    assert [segment.name for segment in segments] == [
        entities.BudgetTrackerName.EXPENSES,
    ]


def test_no_segments_at_all_when_nothing_is_allocated() -> None:
    # Arrange - the caller draws a caption rather than an empty ring.

    # Act
    segments = allocation_ring.slices([], income=500.0)

    # Assert
    assert segments == []


def test_unallocated_goes_negative_once_over_allocated(
    build_root: "Callable[..., read_models.CategoryView]",
) -> None:
    # Arrange - the sign is what the render path reads to pick the alarm state.
    budget = 800.0
    income = 500.0
    roots = [build_root(budget=budget)]

    # Act
    left_over = allocation_ring.unallocated(roots, income=income)

    # Assert
    assert left_over == income - budget


@pytest.mark.parametrize(
    "palette",
    [allocation_ring.LIGHT, allocation_ring.DARK],
    ids=["light", "dark"],
)
def test_every_budget_tracker_has_a_slice_colour(
    palette: allocation_ring.Palette,
) -> None:
    # Arrange - an unmapped tracker would silently take the remainder's grey.

    # Act
    named = {name: palette.tracker(name) for name in entities.BudgetTrackerName}

    # Assert
    assert all(colour != palette.unallocated for colour in named.values())
