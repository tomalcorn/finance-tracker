"""Unit tests for the entities module."""

import datetime
import uuid

from domain import entities


class TestOwnershipDefaults:
    """Tests for the ownership dimension on FinanceTrackerBaseModel."""

    def test_ownership_type_defaults_to_personal(self) -> None:
        # Arrange / Act
        model = entities.BankAccountModel(user_id="test-user", name="Current")
        # Assert
        assert model.ownership_type is entities.OwnershipType.PERSONAL

    def test_joint_account_id_defaults_to_none(self) -> None:
        # Arrange / Act
        model = entities.BankAccountModel(user_id="test-user", name="Current")
        # Assert
        assert model.joint_account_id is None

    def test_accepts_joint_ownership_with_account_id(self) -> None:
        # Arrange
        joint_id = uuid.uuid4()
        # Act
        model = entities.BankAccountModel(
            user_id="test-user",
            name="Joint Current",
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=joint_id,
        )
        # Assert
        assert all(
            [
                model.ownership_type is entities.OwnershipType.JOINT,
                model.joint_account_id == joint_id,
            ],
        )


class TestJointAccountModel:
    """Tests for JointAccountModel."""

    def test_created_at_defaults_to_none(self) -> None:
        # Arrange / Act
        model = entities.JointAccountModel(name="Our Account")
        # Assert
        assert model.created_at is None

    def test_created_at_populated_from_db_alias(self) -> None:
        # Arrange
        created = datetime.datetime(2026, 7, 14, tzinfo=datetime.UTC)
        # Act
        model = entities.JointAccountModel.model_validate(
            {"name": "Our Account", "_created_at": created},
        )
        # Assert
        assert model.created_at == created

    def test_created_at_excluded_from_serialisation(self) -> None:
        # Arrange
        created = datetime.datetime(2026, 7, 14, tzinfo=datetime.UTC)
        model = entities.JointAccountModel(name="Our Account", created_at=created)
        # Act
        dumped = model.model_dump(mode="json")
        # Assert
        assert all(key not in dumped for key in ("created_at", "_created_at"))


class TestJointAccountMemberModel:
    """Tests for JointAccountMemberModel."""

    def test_links_user_to_joint_account(self) -> None:
        # Arrange
        joint_id = uuid.uuid4()
        # Act
        member = entities.JointAccountMemberModel(
            joint_account_id=joint_id,
            user_id="test-user",
        )
        # Assert
        assert all([member.joint_account_id == joint_id, member.user_id == "test-user"])


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
