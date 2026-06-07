"""Pure domain entities for backend data."""

import datetime
import enum
import uuid
from typing import Annotated, Literal

import pydantic

type JsonDict = dict[str, pydantic.JsonValue]


class FinanceTrackerBaseModel(pydantic.BaseModel):
    """Base model for finance tracker entities."""

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the item.",
        default_factory=uuid.uuid4,
    )
    user_id: Annotated[
        str,
        pydantic.Field(
            description="The Auth0 user ID who owns the item.",
        ),
    ]
    name: Annotated[str, pydantic.Field(description="The name of the item.")] = ""


class BankAccountModel(FinanceTrackerBaseModel):
    """Model representing a bank account."""

    starting_balance: Annotated[
        float,
        pydantic.Field(description="The starting balance of the bank account."),
    ] = 0.0


class BudgetTrackerName(enum.StrEnum):
    """Fixed names for budget tracker rows."""

    EXPENSES = "Expenses"
    JOINT = "Joint"
    ONE_OFFS = "One-offs"
    SAVINGS = "Savings"


class BudgetTrackerItemModel(FinanceTrackerBaseModel):
    """Model representing a budget tracker item."""

    name: Annotated[
        BudgetTrackerName,
        pydantic.Field(description="The budget tracker category name."),
    ]
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
    budget_tracker_ids: list[uuid.UUID] | None = pydantic.Field(
        description="List of associated budget tracker item IDs.",
        default=None,
    )


class OneOffItemModel(FinanceTrackerBaseModel):
    """Model representing a one-off savings goal item."""

    cost: Annotated[
        float,
        pydantic.Field(description="The target cost of the one-off item."),
    ] = 0.0
    current_month: Annotated[
        float,
        pydantic.Field(description="The amount pledged for the current month."),
    ] = 0.0
    banked: Annotated[
        float,
        pydantic.Field(description="The amount banked from past months."),
    ] = 0.0
    budget_tracker_id: uuid.UUID | None = pydantic.Field(
        description="The associated budget tracker item ID.",
        default=None,
    )


class IncomeSourceModel(FinanceTrackerBaseModel):
    """Model representing an income source."""

    budget_tracker_ids: list[uuid.UUID] = pydantic.Field(
        description="List of associated budget tracker item IDs.",
        default_factory=list,
    )


class SubscriptionModel(FinanceTrackerBaseModel):
    """Model representing a recurring subscription."""

    amount: Annotated[
        float,
        pydantic.Field(description="The subscription amount per cadence."),
    ] = 0.0
    cadence: Annotated[
        Literal["weekly", "monthly", "quarterly", "biannually", "yearly"],
        pydantic.Field(description="The payment frequency."),
    ] = "monthly"
    bank_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The associated bank account ID."),
    ]
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated expense source ID."),
    ] = None
    start_date: datetime.date = pydantic.Field(
        description="The date the subscription starts.",
        default_factory=datetime.date.today,
    )
    end_date: Annotated[
        datetime.date | None,
        pydantic.Field(description="The date the subscription ends (None = ongoing)."),
    ] = None
    is_active: Annotated[
        bool,
        pydantic.Field(description="Whether the subscription is currently active."),
    ] = True


class _PaymentBaseModel(FinanceTrackerBaseModel):
    """Base model for payment entries."""

    payment_date: datetime.date = pydantic.Field(
        description="The date of the payment.",
        default_factory=datetime.date.today,
    )
    checked: Annotated[
        bool,
        pydantic.Field(description="Whether the payment has been checked/verified."),
    ] = False
    bank_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The associated bank account ID."),
    ]
    subscription_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The originating subscription ID, if any."),
    ] = None


class ExpensePaymentModel(_PaymentBaseModel):
    """Model representing an expense payment."""

    payment_type: Annotated[
        Literal["expense"],
        pydantic.Field(description="The type of payment."),
    ] = "expense"
    expense: Annotated[
        float,
        pydantic.Field(description="The expense amount for the payment."),
    ] = 0.0
    income: Annotated[
        float,
        pydantic.Field(description="The income amount (always 0 for expenses)."),
    ] = 0.0
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated expense source ID."),
    ] = None


class IncomePaymentModel(_PaymentBaseModel):
    """Model representing an income payment."""

    payment_type: Annotated[
        Literal["income"],
        pydantic.Field(description="The type of payment."),
    ] = "income"
    income: Annotated[
        float,
        pydantic.Field(description="The income amount for the payment."),
    ] = 0.0
    expense: Annotated[
        float,
        pydantic.Field(description="The expense amount (always 0 for income)."),
    ] = 0.0
    income_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated income source ID."),
    ] = None


class BackendUpdates(pydantic.BaseModel):
    """Model for tracking pending creates, edits and deletes before committing."""

    added_rows: Annotated[
        list[JsonDict],
        pydantic.Field(description="List of new row data entries."),
    ] = []
    edited_rows: Annotated[
        dict[str, JsonDict],
        pydantic.Field(description="Dictionary of IDs to updated row data."),
    ] = {}
    deleted_rows: Annotated[
        list[str],
        pydantic.Field(description="List of row ids to be deleted."),
    ] = []
