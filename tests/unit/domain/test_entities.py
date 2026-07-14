"""Unit tests for the entities module."""

import uuid

import pytest

from domain import entities, errors, read_models


class TestRequireJointAccountId:
    """Tests for the joint-ownership invariant helper."""

    def test_rejects_joint_without_account_id(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(errors.MissingJointAccountError):
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
        with pytest.raises(errors.MissingJointAccountError):
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
        with pytest.raises(errors.MissingJointAccountError):
            read_models.BankAccountView.model_validate(row)


class TestOwnershipSerialisation:
    """The ownership columns must reach the write path (migration 0002)."""

    def test_ownership_fields_are_serialised(self) -> None:
        # Arrange
        account = entities.BankAccountModel(user_id="test-user")
        # Act
        dumped = account.model_dump(mode="json")
        # Assert
        assert {"ownership_type", "joint_account_id"} <= dumped.keys()
