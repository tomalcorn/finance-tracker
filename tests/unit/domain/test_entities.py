"""Unit tests for the entities module."""

import uuid

import pydantic
import pytest

from domain import entities, read_models


class TestRequireJointAccountId:
    """Tests for the joint-ownership invariant helper."""

    def test_rejects_joint_without_account_id(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="joint_account_id is required"):
            entities.require_joint_account_id(entities.OwnershipType.JOINT, None)

    @pytest.mark.parametrize(
        ("ownership_type", "joint_account_id"),
        [
            (entities.OwnershipType.PERSONAL, None),
            (entities.OwnershipType.PERSONAL, uuid.uuid4()),
            (entities.OwnershipType.JOINT, uuid.uuid4()),
        ],
    )
    def test_allows_valid_combinations(
        self,
        ownership_type: entities.OwnershipType,
        joint_account_id: uuid.UUID | None,
    ) -> None:
        # Act
        result = entities.require_joint_account_id(ownership_type, joint_account_id)
        # Assert
        assert result is None


class TestJointOwnershipValidator:
    """Tests that the invariant is wired into the write and read models."""

    def test_entity_rejects_joint_without_account_id(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(pydantic.ValidationError):
            entities.BankAccountModel(
                user_id="test-user",
                ownership_type=entities.OwnershipType.JOINT,
            )

    def test_view_rejects_joint_without_account_id(self) -> None:
        # Arrange
        row = {
            "id": uuid.uuid4(),
            "user_id": "test-user",
            "name": "Joint Current",
            "starting_balance": 0.0,
            "current_balance": 0.0,
            "ownership_type": entities.OwnershipType.JOINT,
        }
        # Act / Assert
        with pytest.raises(pydantic.ValidationError):
            read_models.BankAccountView.model_validate(row)


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
