"""Unit tests for the backend models module."""

import uuid
from unittest import mock

from libs import data_client
from libs.models import backend_models


class TestExpenseSourceModel:
    """Tests for ExpenseSourceModel.budget_tracker_ids validator."""

    def test_defaults_to_expenses_when_no_ids_provided(self) -> None:
        expected_id = uuid.uuid4()
        mock_data = [
            {"id": str(expected_id), "name": "Expenses"},
            {"id": str(uuid.uuid4()), "name": "One-offs"},
        ]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.ExpenseSourceModel(
                user_id="test-user",
                name="Groceries",
            )
            assert model.budget_tracker_ids == [expected_id]

    def test_keeps_explicit_ids(self) -> None:
        explicit_id = uuid.uuid4()
        model = backend_models.ExpenseSourceModel(
            user_id="test-user",
            name="Joint",
            budget_tracker_ids=[explicit_id],
        )
        assert model.budget_tracker_ids == [explicit_id]

    def test_returns_empty_list_when_no_expenses_bt(self) -> None:
        mock_data = [{"id": str(uuid.uuid4()), "name": "One-offs"}]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.ExpenseSourceModel(
                user_id="test-user",
                name="Test",
            )
            assert model.budget_tracker_ids == []


class TestOneOffItemModel:
    """Tests for the OneOffItemModel."""

    def test_budget_tracker_id_returns_uuid_when_one_offs_exists(self) -> None:
        """Test budget_tracker_id returns correct UUID when 'One-offs' row exists."""
        expected_id = uuid.uuid4()
        mock_data = [
            {"id": str(uuid.uuid4()), "name": "Expenses"},
            {"id": str(expected_id), "name": "One-offs"},
        ]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.OneOffItemModel(
                id=uuid.uuid4(),
                user_id="test-user",
                name="Test Item",
                cost=100.0,
            )
            assert model.budget_tracker_id == expected_id

    def test_budget_tracker_id_returns_none_when_no_one_offs(self) -> None:
        """Test budget_tracker_id returns None when no 'One-offs' row exists."""
        mock_data = [{"id": str(uuid.uuid4()), "name": "Expenses"}]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.OneOffItemModel(
                id=uuid.uuid4(),
                user_id="test-user",
                name="Test Item",
            )
            assert model.budget_tracker_id is None
