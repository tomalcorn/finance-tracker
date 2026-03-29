"""Pydantic models for backend model validation."""

import datetime
import uuid
from typing import Annotated

import pydantic


class FinanceTrackerBaseModel(pydantic.BaseModel):
    """Base model for finance tracker models."""

    id: Annotated[
        uuid.UUID,
        pydantic.Field(
            description="The unique identifier for the item.",
            default_factory=uuid.uuid4,
        ),
    ]
    user_id: Annotated[
        uuid.UUID,
        pydantic.Field(
            description="The unique identifier for the user who owns the item.",
        ),
    ]
    name: Annotated[str, pydantic.Field(description="The name of the item.")] = ""


class BankAccountModel(FinanceTrackerBaseModel):
    """Model representing a bank account."""

    starting_balance: Annotated[
        float,
        pydantic.Field(description="The starting balance of the bank account."),
    ] = 0.0


class BudgetTrackerItemModel(FinanceTrackerBaseModel):
    """Model representing a budget tracker item."""

    total_budget: Annotated[
        float,
        pydantic.Field(description="The total budget amount."),
    ] = 0.0


class ExpenseSourceModel(FinanceTrackerBaseModel):
    """Model representing an expense source."""

    budget: Annotated[
        float,
        pydantic.Field(description="The budget amount for the expense source."),
    ] = 0.0
    budget_tracker_ids: Annotated[
        list[uuid.UUID],
        pydantic.Field(description="List of associated budget tracker item IDs."),
    ] = []


class FunSpendingItemModel(FinanceTrackerBaseModel):
    """Model representing a fun spending item."""

    cost: Annotated[
        float,
        pydantic.Field(description="The cost of the fun spending item."),
    ] = 0.0
    current_month: Annotated[
        float,
        pydantic.Field(description="The amount pledged for the current month."),
    ] = 0.0
    banked: Annotated[
        float,
        pydantic.Field(description="The amount banked from past months."),
    ] = 0.0
    budget_tracker_id: Annotated[
        uuid.UUID,
        pydantic.Field(
            description="The associated budget tracker item ID.",
            default_factory=uuid.uuid4,
        ),
    ]


class IncomeSourceModel(FinanceTrackerBaseModel):
    """Model representing an income source."""

    budget_tracker_ids: Annotated[
        list[uuid.UUID],
        pydantic.Field(description="List of associated budget tracker item IDs."),
    ] = []


class PaymentsModel(FinanceTrackerBaseModel):
    """Model representing a payment."""

    income: Annotated[
        float | None,
        pydantic.Field(description="The income amount for the payment."),
    ] = None
    expense: Annotated[
        float | None,
        pydantic.Field(description="The expense amount for the payment."),
    ] = None
    income_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated income source ID."),
    ] = None
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated expense source ID."),
    ] = None
    payment_date: Annotated[
        datetime.date,
        pydantic.Field(
            description="The date of the payment.",
            default_factory=datetime.date.today,
        ),
    ]
    checked: Annotated[
        bool,
        pydantic.Field(description="Whether the payment has been checked/verified."),
    ] = False
    bank_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The associated bank account ID."),
    ]


class UserModel(pydantic.BaseModel):
    """Model representing a user."""

    id: Annotated[
        uuid.UUID,
        pydantic.Field(
            description="TO BE DEPRECATED. The unique identifier for the user.",
        ),
    ] = uuid.uuid4()
    first_name: Annotated[
        str,
        pydantic.Field(description="The first name of the user."),
    ] = ""
    last_name: Annotated[
        str,
        pydantic.Field(description="The last name of the user."),
    ] = ""
