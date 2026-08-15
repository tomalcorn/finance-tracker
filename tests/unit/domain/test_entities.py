"""Unit tests for the entities module."""

import datetime
import uuid

import pydantic
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


class TestCategoryAccrual:
    """A pot fills up over months; everything else resets monthly (#248)."""

    @staticmethod
    def _pot(
        *,
        parent_id: uuid.UUID | None,
        cost: float | None = 200.0,
        starting_balance: float | None = 150.0,
    ) -> entities.CategoryModel:
        """Build a multi-month pot, complete unless a test breaks it."""
        return entities.CategoryModel(
            user_id="test-user",
            name="Festival tickets",
            parent_id=parent_id,
            accrual=entities.AccrualPeriod.MULTI_MONTH,
            cost=cost,
            starting_balance=starting_balance,
        )

    def test_a_complete_pot_is_accepted(self) -> None:
        # Arrange / Act
        pot = self._pot(parent_id=uuid.uuid4())

        # Assert
        assert pot.is_pot

    def test_a_monthly_category_is_not_a_pot(self) -> None:
        # Arrange / Act
        category = entities.CategoryModel(user_id="test-user", name="Groceries")

        # Assert
        assert not category.is_pot

    def test_a_pot_may_start_below_zero(self) -> None:
        # Arrange - a starting balance is unconstrained in sign, like a bank
        # account's, which is what lets money be moved out of a pot that was
        # filled by payments
        moved_out = -20.0

        # Act
        pot = self._pot(parent_id=uuid.uuid4(), starting_balance=moved_out)

        # Assert
        assert pot.starting_balance == moved_out

    @pytest.mark.parametrize(
        ("cost", "starting_balance"),
        [(None, 150.0), (200.0, None)],
    )
    def test_a_pot_needs_both_fields(
        self,
        cost: float | None,
        starting_balance: float | None,
    ) -> None:
        # Arrange - without a cost there is nothing to measure how full it is
        # against, and without a starting balance there is no figure to
        # accumulate onto. The DB CHECK holds the same rule, since a grid edit
        # reaches the columns through apply_edits without passing through here

        # Act / Assert
        with pytest.raises(errors.IncompleteMultiMonthCategoryError):
            self._pot(
                parent_id=uuid.uuid4(),
                cost=cost,
                starting_balance=starting_balance,
            )

    def test_the_incomplete_error_names_the_missing_field(self) -> None:
        # Arrange / Act
        with pytest.raises(errors.IncompleteMultiMonthCategoryError) as exc_info:
            self._pot(parent_id=uuid.uuid4(), cost=None)

        # Assert
        assert exc_info.value.missing == ["cost"]

    @pytest.mark.parametrize(
        ("cost", "starting_balance"),
        [(10.0, None), (None, 10.0)],
    )
    def test_a_monthly_category_may_not_carry_pot_fields(
        self,
        cost: float | None,
        starting_balance: float | None,
    ) -> None:
        # Arrange - nothing would ever read them, so carrying one is a mistake
        # rather than a harmless extra

        # Act / Assert
        with pytest.raises(errors.MonthlyCategoryWithPotFieldsError):
            entities.CategoryModel(
                user_id="test-user",
                name="Groceries",
                parent_id=uuid.uuid4(),
                cost=cost,
                starting_balance=starting_balance,
            )

    def test_a_root_cannot_be_a_pot(self) -> None:
        # Arrange - a root is a monthly allowance, and the roll-up reads its
        # children's monthly figures, so an accruing root would total two
        # different windows at once

        # Act / Assert
        with pytest.raises(errors.MultiMonthRootCategoryError):
            self._pot(parent_id=None)


class TestCategoryTree:
    """A category is a root or a child of one, and never its own parent (#246)."""

    def test_a_category_without_a_parent_is_a_root(self) -> None:
        # Arrange / Act
        category = entities.CategoryModel(user_id="test-user", name="Expenses")

        # Assert
        assert category.is_root

    def test_a_category_with_a_parent_is_not_a_root(self) -> None:
        # Arrange / Act
        category = entities.CategoryModel(
            user_id="test-user",
            name="Groceries",
            parent_id=uuid.uuid4(),
        )

        # Assert
        assert not category.is_root

    def test_a_negative_budget_is_refused(self) -> None:
        # Arrange - a budget is a plan for money going out, so a negative one is
        # not a smaller budget; migration 0022 holds the same rule on the table,
        # which is where a grid edit lands without passing through this model
        # Act / Assert
        with pytest.raises(pydantic.ValidationError):
            entities.CategoryModel(
                user_id="test-user",
                name="Groceries",
                budget=-1.0,
            )

    def test_a_category_cannot_be_its_own_parent(self) -> None:
        # Arrange - the one half of the depth rule visible from a single row;
        # the rest needs the row's siblings and is enforced in the database
        category_id = uuid.uuid4()

        # Act / Assert
        with pytest.raises(errors.SelfParentedCategoryError):
            entities.CategoryModel(
                id=category_id,
                user_id="test-user",
                name="Groceries",
                parent_id=category_id,
            )

    def test_the_error_names_the_category(self) -> None:
        # Arrange
        category_id = uuid.uuid4()

        # Act
        with pytest.raises(errors.SelfParentedCategoryError) as exc_info:
            entities.CategoryModel(
                id=category_id,
                user_id="test-user",
                name="Groceries",
                parent_id=category_id,
            )

        # Assert
        assert exc_info.value.name == "Groceries"


class TestCategoryViewBounds:
    """What categories_view can actually emit, pinned (#247).

    These guard a deliberate *absence*: ``progress`` looks like a 0-100
    percentage and is not one, so a well-meant ``le=100`` would fail the read.
    ``_validated`` raises for the whole batch, not the offending row, so that
    takes the page down rather than one figure.
    """

    @staticmethod
    def _row(**overrides: object) -> dict[str, object]:
        """Return a categories_view row, keyed as the view returns it."""
        return {
            "id": uuid.uuid4(),
            "user_id": "test-user",
            "name": "Eating out",
            "parent_id": uuid.uuid4(),
            "budget": 100.0,
            "current_month": 50.0,
            "remaining": 50.0,
            "progress": 50.0,
            "split": 25.0,
            "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        } | overrides

    def test_progress_may_exceed_one_hundred(self) -> None:
        # Arrange - a budget is there to be overshot, and live data already
        # carries a category at 206%
        overspent = 206.02
        row = self._row(
            current_month=overspent,
            remaining=-106.02,
            progress=overspent,
        )

        # Act
        view = read_models.CategoryView.model_validate(row)

        # Assert
        assert view.progress == overspent

    def test_progress_may_go_negative(self) -> None:
        # Arrange - a refund is a negative expense (#230), so a month of nothing
        # but reimbursements nets out below zero
        refunded = -15.0
        row = self._row(current_month=refunded, remaining=115.0, progress=refunded)

        # Act
        view = read_models.CategoryView.model_validate(row)

        # Assert
        assert view.progress == refunded

    def test_split_may_exceed_one_hundred(self) -> None:
        # Arrange - a category can be allowed more than what it is measured
        # against, e.g. a root budgeted above the income funding it
        oversized_share = 140.0
        row = self._row(split=oversized_share)

        # Act
        view = read_models.CategoryView.model_validate(row)

        # Assert
        assert view.split == oversized_share

    def test_split_cannot_be_negative(self) -> None:
        # Arrange - the view divides a non-negative budget by a denominator it
        # has already checked is positive, so a negative share is not a value
        # the view can produce
        row = self._row(split=-1.0)

        # Act / Assert
        with pytest.raises(pydantic.ValidationError):
            read_models.CategoryView.model_validate(row)


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
