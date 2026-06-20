"""Unit tests for the entities module."""

import uuid

from domain import entities


class TestExpenseSourceModel:
    """Tests for ExpenseSourceModel.budget_tracker_ids field."""

    def test_defaults_to_none_when_no_ids_provided(self) -> None:
        model = entities.ExpenseSourceModel(
            user_id="test-user",
            name="Groceries",
        )
        assert model.budget_tracker_ids is None

    def test_keeps_explicit_ids(self) -> None:
        explicit_id = uuid.uuid4()
        model = entities.ExpenseSourceModel(
            user_id="test-user",
            name="Joint",
            budget_tracker_ids=[explicit_id],
        )
        assert model.budget_tracker_ids == [explicit_id]


class TestOneOffItemModel:
    """Tests for the OneOffItemModel."""

    def test_budget_tracker_id_defaults_to_none(self) -> None:
        model = entities.OneOffItemModel(
            id=uuid.uuid4(),
            user_id="test-user",
            name="Test Item",
            cost=100.0,
        )
        assert model.budget_tracker_id is None

    def test_budget_tracker_id_accepts_explicit_value(self) -> None:
        expected_id = uuid.uuid4()
        model = entities.OneOffItemModel(
            id=uuid.uuid4(),
            user_id="test-user",
            name="Test Item",
            cost=100.0,
            budget_tracker_id=expected_id,
        )
        assert model.budget_tracker_id == expected_id
