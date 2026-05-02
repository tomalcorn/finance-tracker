"""Unit tests for the backend models module."""

import uuid
from unittest import mock

from libs import data_client
from libs.models import backend_models


class TestOneOffItemModel:
    """Tests for the OneOffItemModel."""

    def test_budget_tracker_id_returns_uuid_when_one_offs_exists(self) -> None:
        """Test budget_tracker_id returns  correct UUID when 'one-offs' row exists."""
        expected_id = uuid.uuid4()
        mock_data = [
            {"id": str(uuid.uuid4()), "name": "expenses"},
            {"id": str(expected_id), "name": "one-offs"},
        ]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.OneOffItemModel(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                name="Test Item",
                cost=100.0,
            )
            assert model.budget_tracker_id == expected_id

    def test_budget_tracker_id_case_insensitive(self) -> None:
        """Test budget_tracker_id matches 'One-Offs' case-insensitively."""
        expected_id = uuid.uuid4()
        mock_data = [{"id": str(expected_id), "name": "One-Offs"}]
        with mock.patch.object(data_client, "get_data", return_value=mock_data):
            model = backend_models.OneOffItemModel(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                name="Test Item",
            )
            assert model.budget_tracker_id == expected_id
