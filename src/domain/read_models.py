"""Frozen read models representing view rows (query side of CQRS-lite).

Most models correspond to one view in the Supabase schema, carrying the
view's computed columns alongside the base writable-table columns. The
exception is ``PaymentView``, which reads the raw ``payments`` table (payments
have no view) and therefore carries no computed columns.
"""

import datetime
import uuid
from typing import Annotated, Literal

import pydantic

from domain.entities import BudgetTrackerName


class _ViewBase(pydantic.BaseModel):
    """Shared base for all view read models."""

    model_config = pydantic.ConfigDict(frozen=True)

    id: Annotated[uuid.UUID, pydantic.Field(description="Unique row identifier.")]
    user_id: Annotated[str, pydantic.Field(description="Owning user's Auth0 ID.")]
    name: Annotated[str, pydantic.Field(description="Display name.")]


class BankAccountView(_ViewBase):
    """Read model for bank_accounts_view."""

    starting_balance: Annotated[
        float,
        pydantic.Field(description="The starting balance of the bank account."),
    ]
    current_balance: Annotated[
        float,
        pydantic.Field(description="Computed: starting_balance plus net payments."),
    ]


class BudgetTrackerView(_ViewBase):
    """Read model for budget_tracker_view."""

    name: Annotated[
        BudgetTrackerName,
        pydantic.Field(description="The budget tracker category name."),
    ]
    total_budget: Annotated[
        float,
        pydantic.Field(description="The total budget amount."),
    ]
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of payments in the current month."),
    ]
    remaining: Annotated[
        float,
        pydantic.Field(description="total_budget minus current_month."),
    ]
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of budget consumed (0-100)."),
    ]
    split: Annotated[
        float,
        pydantic.Field(description="This tracker's share of total spend (0-100)."),
    ]


class ExpenseSourceView(_ViewBase):
    """Read model for expense_sources_view."""

    budget: Annotated[
        float,
        pydantic.Field(description="The budget amount for the expense source."),
    ]
    budget_tracker_ids: Annotated[
        list[uuid.UUID] | None,
        pydantic.Field(description="Associated budget tracker IDs."),
    ] = None
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of expense payments in the current month."),
    ]
    remaining: Annotated[
        float,
        pydantic.Field(description="budget minus current_month."),
    ]
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of budget consumed (0-100)."),
    ]
    split: Annotated[
        float,
        pydantic.Field(description="Share of total expense spend (0-100)."),
    ]


class IncomeSourceView(_ViewBase):
    """Read model for income_sources_view."""

    budget_tracker_ids: Annotated[
        list[uuid.UUID],
        pydantic.Field(description="Associated budget tracker IDs."),
    ]
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of income payments in the current month."),
    ]


class SubscriptionView(_ViewBase):
    """Read model for subscriptions_view."""

    amount: Annotated[
        float,
        pydantic.Field(description="The subscription amount per cadence."),
    ]
    cadence: Annotated[
        Literal["weekly", "monthly", "quarterly", "biannually", "yearly"],
        pydantic.Field(description="The payment frequency."),
    ]
    bank_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The associated bank account ID."),
    ]
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated expense source ID."),
    ] = None
    start_date: Annotated[
        datetime.date,
        pydantic.Field(description="The date the subscription starts."),
    ]
    end_date: Annotated[
        datetime.date | None,
        pydantic.Field(description="The date the subscription ends (None = ongoing)."),
    ] = None
    is_active: Annotated[
        bool,
        pydantic.Field(description="Whether the subscription is currently active."),
    ]
    monthly_cost: Annotated[
        float,
        pydantic.Field(description="amount normalised to a monthly equivalent."),
    ]


class PaymentView(_ViewBase):
    """Read model for payment rows.

    Payments have no SQL view — this reads the raw ``payments`` table, so it
    carries no computed columns, only the flat union of expense and income
    payment fields. The source-id columns are nullable because only one of
    ``expense_source_id`` / ``income_source_id`` is set per row.
    """

    payment_date: Annotated[
        datetime.date,
        pydantic.Field(description="The date of the payment."),
    ]
    payment_type: Annotated[
        Literal["expense", "income"],
        pydantic.Field(description="Whether the row is an expense or income entry."),
    ]
    expense: Annotated[
        float,
        pydantic.Field(description="The expense amount (0 for income rows)."),
    ]
    income: Annotated[
        float,
        pydantic.Field(description="The income amount (0 for expense rows)."),
    ]
    checked: Annotated[
        bool,
        pydantic.Field(description="Whether the payment has been checked/verified."),
    ]
    bank_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The associated bank account ID."),
    ]
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated expense source ID, if any."),
    ] = None
    income_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated income source ID, if any."),
    ] = None
    subscription_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The originating subscription ID, if any."),
    ] = None


class OneOffView(_ViewBase):
    """Read model for one_offs_view."""

    cost: Annotated[
        float,
        pydantic.Field(description="The target cost of the one-off item."),
    ]
    current_month: Annotated[
        float,
        pydantic.Field(description="The amount pledged for the current month."),
    ]
    banked: Annotated[
        float,
        pydantic.Field(description="The amount banked from past months."),
    ]
    budget_tracker_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The associated budget tracker item ID."),
    ] = None
    remaining: Annotated[
        float,
        pydantic.Field(description="cost minus banked."),
    ]
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of cost banked (0-100)."),
    ]
    split: Annotated[
        float,
        pydantic.Field(description="Share of total one-off spend (0-100)."),
    ]
