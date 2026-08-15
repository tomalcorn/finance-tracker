"""Frozen read models representing view rows (query side of CQRS-lite).

Most models correspond to one view in the Supabase schema, carrying the
view's computed columns alongside the base writable-table columns. The
exception is ``PaymentView``, which reads the raw ``payments`` table (payments
have no view) and therefore carries no computed columns.
"""

import datetime
import uuid
from typing import Annotated, Literal, Self

import pydantic

from domain import entities


class _ViewBase(pydantic.BaseModel):
    """Shared base for all view read models."""

    # populate_by_name: rows arrive from the database keyed by the physical
    # column name, but a caller constructing one directly uses the field name.
    model_config = pydantic.ConfigDict(frozen=True, populate_by_name=True)

    id: Annotated[uuid.UUID, pydantic.Field(description="Unique row identifier.")]
    user_id: Annotated[str, pydantic.Field(description="Owning user's ID.")]
    name: Annotated[str, pydantic.Field(description="Display name.")]
    created_at: Annotated[
        datetime.datetime,
        pydantic.Field(
            alias="_created_at",
            description="When the row was inserted; the grid's final sort key.",
        ),
    ]
    ownership_type: Annotated[
        entities.OwnershipType,
        pydantic.Field(
            description="Whether the row is personal or shared via a joint account.",
        ),
    ] = entities.OwnershipType.PERSONAL
    joint_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description="The joint account this row belongs to when it is joint.",
        ),
    ] = None

    @pydantic.model_validator(mode="after")
    def _check_joint_account_id(self) -> Self:
        """Ensure a joint-owned row carries a joint account reference."""
        entities.require_joint_account_id(self.ownership_type, self.joint_account_id)
        return self


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
        entities.BudgetTrackerName,
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


class CategoryView(_ViewBase):
    """Read model for categories_view.

    One model for both levels of the tree: the view computes the same four
    figures for a root and for a child, so the level a row sits at is carried by
    ``parent_id`` rather than by which model was read.
    """

    parent_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The category this one sits under, if any."),
    ] = None
    budget: Annotated[
        pydantic.NonNegativeFloat,
        pydantic.Field(description="What this category is allowed each month."),
    ]
    accrual: Annotated[
        entities.AccrualPeriod,
        pydantic.Field(
            description="The window this row's payments were totalled over.",
        ),
    ] = entities.AccrualPeriod.MONTHLY
    cost: Annotated[
        pydantic.NonNegativeFloat,
        pydantic.Field(description="What a pot needs to reach; unused if monthly."),
    ] = 0.0
    starting_balance: Annotated[
        float,
        pydantic.Field(
            description="What a pot held before payments could reach it.",
        ),
    ] = 0.0
    current_month: Annotated[
        float,
        pydantic.Field(
            description=(
                "Computed: this category's own payments plus its children's over "
                "the current month — or, for a pot, its starting balance plus "
                "everything paid in since. Signed, so a month whose refunds "
                "outweigh its spending nets out below zero."
            ),
        ),
    ]
    remaining: Annotated[
        float,
        pydantic.Field(
            description=(
                "What is left: budget minus current_month, or for a pot its cost "
                "minus what is in it. Negative once overspent."
            ),
        ),
    ]
    # Deliberately unconstrained, both ends. Upper: `progress` is spend over
    # budget, and a budget is there to be overshot — live data already carries a
    # category at 206%, so `le=100` would fail the read for every row in the
    # batch. Lower: a refund is a negative expense (#230), so a month of nothing
    # but reimbursements puts it below zero. Only the *display* is 0-100, and
    # that clamping belongs to ProgressColumn, not here.
    progress: Annotated[
        float,
        pydantic.Field(
            description=(
                "Percentage of budget consumed. Exceeds 100 when overspent, and "
                "goes negative when refunds outweigh spending."
            ),
        ),
    ]
    split: Annotated[
        pydantic.NonNegativeFloat,
        pydantic.Field(
            description=(
                "A child's share of its parent's budget, or a root's share of "
                "total income. Non-negative, but exceeds 100 when a category is "
                "allowed more than what it is measured against."
            ),
        ),
    ]

    @property
    def is_root(self) -> bool:
        """Whether this is a top-level category rather than a subcategory."""
        return self.parent_id is None

    @property
    def is_pot(self) -> bool:
        """Whether this category fills up over months rather than resetting."""
        return self.accrual is entities.AccrualPeriod.MULTI_MONTH


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
        pydantic.Field(
            description="Sum of income payments in the rolled-up month.",
        ),
    ]
    income_roll_up_period: Annotated[
        entities.IncomeRollUpPeriod,
        pydantic.Field(
            description="The month ``current_month`` was totalled over.",
        ),
    ] = entities.IncomeRollUpPeriod.CURRENT_MONTH


class UserSettingsView(_ViewBase):
    """Read model for user_settings rows.

    Settings have no SQL view — this reads the raw ``user_settings`` table, so
    it carries no computed columns.
    """

    income_roll_up_period: Annotated[
        entities.IncomeRollUpPeriod,
        pydantic.Field(
            description="The month income sources total their payments over.",
        ),
    ] = entities.IncomeRollUpPeriod.CURRENT_MONTH


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
    category_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The category the row is attributed to."),
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
    joint_income_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description=(
                "The joint income source a contribution's income leg is booked "
                "against. Set means this row is a joint contribution."
            ),
        ),
    ] = None
    joint_bank_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description="The joint bank account a contribution arrives in.",
        ),
    ] = None


class PaymentView(_ViewBase):
    """Read model for payment rows.

    Payments have no SQL view — this reads the raw ``payments`` table, so it
    carries no computed columns, only the flat union of expense and income
    payment fields. The source-id columns are nullable because only one of
    ``category_id`` / ``income_source_id`` is set per row.
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
    category_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The category the payment is attributed to."),
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


class QuickButtonView(_ViewBase):
    """Read model for quick_buttons rows.

    Quick buttons have no SQL view — this reads the raw ``quick_buttons`` table,
    so it carries no computed columns.
    """

    mode: Annotated[
        entities.QuickButtonMode,
        pydantic.Field(description="Whether a tap logs the preset or asks first."),
    ]
    payment_name: Annotated[
        str | None,
        pydantic.Field(description="The name to log the payment under, if preset."),
    ] = None
    expense: Annotated[
        float | None,
        pydantic.Field(description="The expense amount a tap logs."),
    ] = None
    bank_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The bank account the payment comes from."),
    ] = None
    category_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The category the payment is booked to."),
    ] = None
    icon: Annotated[
        str | None,
        pydantic.Field(description="An optional emoji shown before the name."),
    ] = None
    display_order: Annotated[
        int,
        pydantic.Field(description="Position of the button in the grid."),
    ]


class JointAccountView(pydantic.BaseModel):
    """Read model for joint_accounts rows.

    Does not extend ``_ViewBase``: a joint account has no owning ``user_id``
    and no ownership dimension of its own.
    """

    model_config = pydantic.ConfigDict(frozen=True)

    id: Annotated[uuid.UUID, pydantic.Field(description="Unique account identifier.")]
    name: Annotated[str, pydantic.Field(description="The name of the joint account.")]


class JointAccountMemberView(pydantic.BaseModel):
    """Read model for joint_account_members rows."""

    model_config = pydantic.ConfigDict(frozen=True)

    id: Annotated[uuid.UUID, pydantic.Field(description="Unique membership row ID.")]
    joint_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The joint account the user is a member of."),
    ]
    user_id: Annotated[
        str,
        pydantic.Field(description="The ID of the member."),
    ]
