"""Unit tests for the category picker's labels and ordering (#251)."""

import uuid
from typing import TYPE_CHECKING

import pytest

from domain import entities
from driving_adapters import lookups

if TYPE_CHECKING:
    from collections.abc import Callable

_USER_ID = "auth0|test-user-1"


@pytest.fixture(name="build_category")
def _build_category() -> "Callable[..., entities.CategoryModel]":
    """Return a builder for a category, a root unless given a parent."""

    def _build(
        name: str,
        parent_id: uuid.UUID | None = None,
    ) -> entities.CategoryModel:
        return entities.CategoryModel(
            user_id=_USER_ID,
            name=name,
            parent_id=parent_id,
        )

    return _build


def test_a_root_keeps_its_bare_name(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange
    root = build_category("Expenses")

    # Act
    labels = lookups.make_category_name_map([root])

    # Assert
    assert labels[str(root.id)] == "Expenses"


def test_a_child_is_prefixed_with_its_parent(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange - the two levels are one flat list in a SelectboxColumn, so the
    # prefix does the work a group header would
    root = build_category("Expenses")
    child = build_category("Groceries", parent_id=root.id)

    # Act
    labels = lookups.make_category_name_map([root, child])

    # Assert
    assert labels[str(child.id)] == "Expenses - Groceries"


def test_each_root_is_followed_by_its_own_children(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange - deliberately interleaved, and not in the order they should come
    # out: the picker's options are `list(map)`, so insertion order is the order
    # a user scans
    expenses = build_category("Expenses")
    one_offs = build_category("One-offs")
    festival = build_category("Festival tickets", parent_id=one_offs.id)
    groceries = build_category("Groceries", parent_id=expenses.id)

    # Act
    labels = lookups.make_category_name_map([festival, one_offs, groceries, expenses])

    # Assert
    assert list(labels.values()) == [
        "Expenses",
        "Expenses - Groceries",
        "One-offs",
        "One-offs - Festival tickets",
    ]


def test_children_of_one_root_are_sorted_by_name(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange
    root = build_category("Expenses")
    children = [build_category(name, parent_id=root.id) for name in ("Travel", "Bills")]

    # Act
    labels = lookups.make_category_name_map([root, *children])

    # Assert
    assert list(labels.values()) == [
        "Expenses",
        "Expenses - Bills",
        "Expenses - Travel",
    ]


def test_a_child_whose_parent_is_absent_keeps_its_bare_name(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange - defensive: a child always carries its root's ownership, so this
    # should not arise. If it ever does, the row stays pickable rather than
    # being labelled after a parent that is not there.
    orphan = build_category("Groceries", parent_id=uuid.uuid4())

    # Act
    labels = lookups.make_category_name_map([orphan])

    # Assert
    assert labels[str(orphan.id)] == "Groceries"


def test_every_category_is_offered(
    build_category: "Callable[..., entities.CategoryModel]",
) -> None:
    # Arrange - membership is unchanged by #251: a payment may be attributed to
    # a root directly, and every child is offered too
    root = build_category("Expenses")
    child = build_category("Groceries", parent_id=root.id)
    other_root = build_category("Savings")

    # Act
    labels = lookups.make_category_name_map([root, child, other_root])

    # Assert
    assert set(labels) == {str(root.id), str(child.id), str(other_root.id)}
