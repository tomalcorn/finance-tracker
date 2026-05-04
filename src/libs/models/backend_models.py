"""Pydantic models for backend model validation."""

import datetime
import uuid
from typing import Annotated, Literal

import pydantic

from libs import data_client


class FinanceTrackerBaseModel(pydantic.BaseModel):
    """Base model for finance tracker models."""

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the item.",
        default_factory=uuid.uuid4,
    )
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

    @pydantic.computed_field
    @property
    def budget_tracker_ids(self) -> list[uuid.UUID]:
        """Compute the list of associated budget tracker item IDs.

        Expense sources should all be connected only to the "expenses" budget tracker
        item, so we can compute this based on the name of the budget tracker item
        rather than needing to store it directly
        """
        rows = data_client.get_data(
            table_name="budget_tracker",
            query_string="id,name",
        )
        if row := next((r for r in rows if r.get("name") == "expenses"), None):
            return [uuid.UUID(str(row["id"]))]
        return []


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

    @pydantic.computed_field
    @property
    def budget_tracker_id(self) -> uuid.UUID | None:
        """Compute the associated budget tracker item ID.

        One-off items should all be connected only to the "one-offs" budget tracker
        item, so we can compute this based on the name of the budget tracker item
        rather than needing to store it directly.
        """
        rows = data_client.get_data(
            table_name="budget_tracker",
            query_string="id,name",
        )
        if row := next(
            (r for r in rows if str(r.get("name", "")).lower() == "one-offs"),
            None,
        ):
            return uuid.UUID(str(row["id"]))
        return None


class IncomeSourceModel(FinanceTrackerBaseModel):
    """Model representing an income source."""

    budget_tracker_ids: Annotated[
        list[uuid.UUID],
        pydantic.Field(description="List of associated budget tracker item IDs."),
    ] = []


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


class UserModel(pydantic.BaseModel):
    """Model representing a user."""

    id: Annotated[
        uuid.UUID,
        pydantic.Field(
            description="TO BE DEPRECATED. The unique identifier for the user.",
        ),
    ] = pydantic.Field(default_factory=uuid.uuid4)
    first_name: Annotated[
        str,
        pydantic.Field(description="The first name of the user."),
    ] = ""
    last_name: Annotated[
        str,
        pydantic.Field(description="The last name of the user."),
    ] = ""
