"""Unit tests for the entities module."""

import datetime
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
            "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
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


class TestQuickButtonAmountValidator:
    """A preset amount must move money, in either direction (#230)."""

    def test_a_negative_preset_is_allowed(self) -> None:
        # Arrange - a standing reimbursement button logs money coming back
        refund = -12.5

        # Act
        button = entities.QuickButtonModel(
            user_id="test-user",
            name="Dinner refund",
            expense=refund,
            bank_account_id=uuid.uuid4(),
        )

        # Assert
        assert button.expense == refund

    @pytest.mark.parametrize(
        "mode",
        [entities.QuickButtonMode.LOG, entities.QuickButtonMode.PROMPT],
    )
    def test_a_zero_preset_is_refused(
        self,
        mode: entities.QuickButtonMode,
    ) -> None:
        # Arrange - zero would log a payment that moves nothing, whichever way the
        # button is set up

        # Act / Assert
        with pytest.raises(errors.ZeroQuickButtonAmountError):
            entities.QuickButtonModel(
                user_id="test-user",
                name="Coffee",
                mode=mode,
                expense=0.0,
                bank_account_id=uuid.uuid4(),
            )

    def test_the_error_names_the_button(self) -> None:
        # Arrange / Act
        with pytest.raises(errors.ZeroQuickButtonAmountError) as exc_info:
            entities.QuickButtonModel(
                user_id="test-user",
                name="Coffee",
                expense=0.0,
                bank_account_id=uuid.uuid4(),
            )

        # Assert
        assert exc_info.value.name == "Coffee"


class TestJointContributionValidator:
    """A contribution subscription must be complete, and must be personal."""

    @staticmethod
    def _subscription(
        *,
        ownership_type: entities.OwnershipType = entities.OwnershipType.PERSONAL,
        joint_account_id: uuid.UUID | None = None,
        joint_income_source_id: uuid.UUID | None = None,
        joint_bank_account_id: uuid.UUID | None = None,
    ) -> entities.SubscriptionModel:
        """Return a subscription varying only its ownership and joint fields."""
        return entities.SubscriptionModel(
            user_id="test-user",
            name="Joint standing order",
            bank_account_id=uuid.uuid4(),
            ownership_type=ownership_type,
            joint_account_id=joint_account_id,
            joint_income_source_id=joint_income_source_id,
            joint_bank_account_id=joint_bank_account_id,
        )

    def test_a_contribution_without_its_destination_is_rejected(self) -> None:
        # Arrange / Act
        with pytest.raises(errors.IncompleteJointContributionError) as exc_info:
            self._subscription(joint_income_source_id=uuid.uuid4())

        # Assert
        assert exc_info.value.missing == ["joint_bank_account_id"]

    def test_a_destination_without_an_income_source_is_rejected(self) -> None:
        # Arrange / Act
        with pytest.raises(errors.IncompleteJointContributionError) as exc_info:
            self._subscription(joint_bank_account_id=uuid.uuid4())

        # Assert
        assert exc_info.value.missing == ["joint_income_source_id"]

    def test_a_joint_owned_subscription_cannot_contribute(self) -> None:
        # Arrange / Act / Assert
        # Only the personal side contributes; a joint row doing so would book an
        # expense in the shared books with no counterpart anywhere.
        with pytest.raises(errors.JointOwnedContributionError):
            self._subscription(
                ownership_type=entities.OwnershipType.JOINT,
                joint_account_id=uuid.uuid4(),
                joint_income_source_id=uuid.uuid4(),
                joint_bank_account_id=uuid.uuid4(),
            )

    def test_a_complete_contribution_is_accepted(self) -> None:
        # Arrange
        sub = self._subscription(
            joint_income_source_id=uuid.uuid4(),
            joint_bank_account_id=uuid.uuid4(),
        )

        # Act / Assert
        assert sub.is_joint_contribution
