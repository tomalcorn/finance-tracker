"""Integration tests for ``categories_view``'s ``split`` against the test DB.

The rule lives entirely in SQL — a CASE inside the view — so no unit test can
reach it. Only a live-schema read exercises what a pot row actually reports,
which is the same reason ``test_int_linked_payments`` exists.

Covers the #262 change: a pot divides its planned spend by the One-offs
tracker's ``remaining``, not its ``budget``, and reads 0% once nothing is left
to allocate. An ordinary monthly subcategory still divides by its parent's
budget, and that non-regression is asserted alongside every case.

⚠️ Needs migration ``0032`` applied to the testing database.
"""

import datetime
import uuid
from collections.abc import Generator, Mapping

import pytest
import st_supabase_connection

from domain import read_models
from driven_adapters.supabase import client

_ROOT_BUDGET = 400.0
"""What the stand-in One-offs tracker is allowed each month."""

_HOLIDAY_BUDGET = 100.0
_LAPTOP_BUDGET = 50.0
"""What each pot plans to put towards itself this month."""

_EXPENSES_BUDGET = 1000.0
_BILLS_BUDGET = 250.0
"""The monthly control pair: a root and a child that must not move."""


@pytest.fixture(name="category_tree")
def _category_tree(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> Generator[dict[str, uuid.UUID]]:
    """Seed two roots — one holding pots, one holding a monthly child.

    Named after the grids they stand in for rather than seeded from the app's
    own roots: the test identity is fresh per run, so nothing exists to reuse,
    and a tree built here can carry the exact budgets the arithmetic needs.
    """
    names = ("one_offs", "holiday", "laptop", "expenses", "bills")
    ids = {name: uuid.uuid4() for name in names}
    rows = [
        {
            "id": str(ids["one_offs"]),
            "user_id": test_user_id,
            "name": "One-offs (test)",
            "budget": _ROOT_BUDGET,
            "accrual": "monthly",
        },
        {
            "id": str(ids["holiday"]),
            "user_id": test_user_id,
            "name": "Holiday",
            "parent_id": str(ids["one_offs"]),
            "budget": _HOLIDAY_BUDGET,
            "accrual": "multi_month",
            "cost": 1000.0,
        },
        {
            "id": str(ids["laptop"]),
            "user_id": test_user_id,
            "name": "Laptop",
            "parent_id": str(ids["one_offs"]),
            "budget": _LAPTOP_BUDGET,
            "accrual": "multi_month",
            "cost": 800.0,
        },
        {
            "id": str(ids["expenses"]),
            "user_id": test_user_id,
            "name": "Expenses (test)",
            "budget": _EXPENSES_BUDGET,
            "accrual": "monthly",
        },
        {
            "id": str(ids["bills"]),
            "user_id": test_user_id,
            "name": "Bills",
            "parent_id": str(ids["expenses"]),
            "budget": _BILLS_BUDGET,
            "accrual": "monthly",
        },
    ]
    # Roots first: a child's parent_id is a foreign key, so the order matters.
    for row in rows:
        connection.table("categories").insert(row).execute()

    yield ids

    # Payments reference categories, and children reference their root, so the
    # teardown unwinds in the order the inserts built it up.
    connection.table("payments").delete().in_(
        "category_id",
        [str(category_id) for category_id in ids.values()],
    ).execute()
    for key in ("holiday", "laptop", "bills", "one_offs", "expenses"):
        connection.table("categories").delete().eq("id", str(ids[key])).execute()


def _bank(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
    category_id: uuid.UUID,
    amount: float,
) -> None:
    """Attribute an expense to a category, dated inside the current month."""
    connection.table("payments").insert(
        {
            "id": str(uuid.uuid4()),
            "user_id": test_user_id,
            "name": "Banked",
            "expense": amount,
            "category_id": str(category_id),
            "payment_date": datetime.datetime.now(tz=datetime.UTC).date().isoformat(),
        },
    ).execute()


def _rows_by_name(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> Mapping[str, read_models.CategoryView]:
    """Read the view through the app's own fetch and validate path.

    Built into ``CategoryView`` rather than read as raw JSON so the read model's
    own bound on ``split`` is part of the assertion: a negative percentage would
    fail validation here before any expected value was compared.
    """
    rows = client.fetch_table(
        "categories_view",
        "*",
        connection,
        {"user_id": test_user_id},
    )
    views = [read_models.CategoryView.model_validate(row) for row in rows]
    return {view.name: view for view in views}


@pytest.mark.parametrize(
    ("banked", "expected_splits"),
    [
        # Nothing banked: remaining is the whole budget, so the shares match
        # what "share of budget" used to report.
        (0.0, {"Holiday": 25.0, "Laptop": 12.5}),
        # Half the month's allowance gone: the same plans now claim a larger
        # share of the 200 left.
        (200.0, {"Holiday": 50.0, "Laptop": 25.0}),
        # Fully allocated — remaining is exactly 0, the denominator guard's
        # boundary.
        (400.0, {"Holiday": 0.0, "Laptop": 0.0}),
        # Overspent — remaining is negative, and the guard keeps `split`
        # non-negative rather than emitting a percentage the read model rejects.
        (500.0, {"Holiday": 0.0, "Laptop": 0.0}),
    ],
    ids=["nothing_banked", "half_banked", "fully_allocated", "overspent"],
)
def test_a_pot_divides_by_the_trackers_remaining(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
    category_tree: dict[str, uuid.UUID],
    banked: float,
    expected_splits: Mapping[str, float],
) -> None:
    """A pot's split is its plan over what its tracker has left to allocate."""
    # Arrange - banked straight onto the root, so the pots' own plans and
    # balances stay where the fixture put them and only the denominator moves.
    if banked:
        _bank(connection, test_user_id, category_tree["one_offs"], banked)

    # Act
    rows = _rows_by_name(connection, test_user_id)

    # Assert
    for name, expected in expected_splits.items():
        assert rows[name].split == pytest.approx(expected)


def test_a_monthly_child_still_divides_by_its_parents_budget(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
    category_tree: dict[str, uuid.UUID],
) -> None:
    """The rule branches on the child's own accrual, so Bills does not move."""
    # Arrange - spend against the monthly root, which would move the answer if
    # `remaining` had become the denominator for every child.
    _bank(connection, test_user_id, category_tree["expenses"], 600.0)

    # Act
    rows = _rows_by_name(connection, test_user_id)

    # Assert
    assert rows["Bills"].split == pytest.approx(
        _BILLS_BUDGET / _EXPENSES_BUDGET * 100,
    )
