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


class TestQuickButtonLoggableValidator:
    """A button that logs on tap must hold everything a payment needs."""

    def test_log_button_rejects_a_missing_amount(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(errors.IncompleteQuickButtonError):
            entities.QuickButtonModel(
                user_id="test-user",
                name="Coffee",
                bank_account_id=uuid.uuid4(),
            )

    def test_log_button_names_every_field_it_is_missing(self) -> None:
        # Arrange / Act
        with pytest.raises(errors.IncompleteQuickButtonError) as exc_info:
            entities.QuickButtonModel(user_id="test-user", name="Coffee")

        # Assert
        assert exc_info.value.missing == ["expense", "bank_account_id"]

    def test_prompt_button_may_leave_the_payment_fields_blank(self) -> None:
        # Arrange - the varying part is exactly what a prompt button defers
        button = entities.QuickButtonModel(
            user_id="test-user",
            name="Groceries",
            mode=entities.QuickButtonMode.PROMPT,
        )

        # Act / Assert
        assert button.expense is None
