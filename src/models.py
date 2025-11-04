"""Pydantic models for backend model validation."""

import datetime
import enum
import uuid

import pydantic


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    CURRENT_USER = enum.auto()


class FinanceTrackerBaseModel(pydantic.BaseModel):
    """Base model for finance tracker models."""

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the item.",
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the user who owns the item.",
        default_factory=uuid.uuid4,
    )
    name: str = pydantic.Field(
        description="The name of the item.",
        default="",
    )


class BankAccountModel(FinanceTrackerBaseModel):
    """Model representing a bank account."""

    balance: float = pydantic.Field(
        description="The balance of the bank account.",
        default=0.0,
    )


class BudgetTrackerItemModel(FinanceTrackerBaseModel):
    """Model representing a budget tracker item."""

    total_budget: float = pydantic.Field(
        description="The total budget amount.",
        default=0.0,
    )


class ExpenseSourceModel(FinanceTrackerBaseModel):
    """Model representing an expense source."""

    budget: float = pydantic.Field(
        description="The budget amount for the expense source.",
        default=0.0,
    )
    budget_tracker_ids: list[uuid.UUID] = pydantic.Field(
        description="List of associated budget tracker item IDs.",
        default_factory=list,
    )


class FunSpendingItemModel(FinanceTrackerBaseModel):
    """Model representing a fun spending item."""

    cost: float = pydantic.Field(
        description="The cost of the fun spending item.",
        default=0.0,
    )
    current_month: float = pydantic.Field(
        description="The amount pledged for the current month.",
        default=0.0,
    )
    banked: float = pydantic.Field(
        description="The amount banked from past months.",
        default=0.0,
    )
    budget_tracker_id: uuid.UUID = pydantic.Field(
        description="The associated budget tracker item ID.",
        default_factory=uuid.uuid4,
    )


class IncomeSourceModel(FinanceTrackerBaseModel):
    """Model representing an income source."""

    budget_tracker_ids: list[str] = pydantic.Field(
        description="List of associated budget tracker item IDs.",
        default_factory=list,
    )


class PaymentsModel(FinanceTrackerBaseModel):
    """Model representing a payment."""

    income: float = pydantic.Field(
        description="The income amount for the payment.",
        default=0.0,
    )
    expense: float = pydantic.Field(
        description="The expense amount for the payment.",
        default=0.0,
    )
    income_source_id: str = pydantic.Field(
        description="The associated income source ID.",
        default="",
    )
    expense_source_id: str = pydantic.Field(
        description="The associated expense source ID.",
        default="",
    )
    payment_date: datetime.date = pydantic.Field(
        description="The date of the payment.",
        default_factory=datetime.date.today,
    )
    checked: bool = pydantic.Field(
        description="Whether the payment has been checked/verified.",
        default=False,
    )
    bank_account_id: str = pydantic.Field(
        description="The associated bank account ID.",
        default="",
    )


class UserModel(pydantic.BaseModel):
    """Model representing a user."""

    first_name: str = pydantic.Field(
        description="The first name of the user.",
        default="",
    )
    last_name: str = pydantic.Field(
        description="The last name of the user.",
        default="",
    )
