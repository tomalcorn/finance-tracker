"""Pure domain entities for backend data."""

import datetime
import enum
import uuid
from collections.abc import Mapping, Sequence
from typing import Annotated, Literal, Self

import pydantic

from domain import errors

type JSON = None | bool | str | int | float | Sequence[JSON] | Mapping[str, JSON]
type JsonDict = dict[str, JSON]


class OwnershipType(enum.StrEnum):
    """Whether an aggregate belongs to one user or a shared joint account."""

    PERSONAL = enum.auto()
    JOINT = enum.auto()


def require_joint_account_id(
    ownership_type: OwnershipType,
    joint_account_id: uuid.UUID | None,
) -> None:
    """Raise if a joint-owned item is missing its joint account reference.

    Args:
        ownership_type: How the item is owned.
        joint_account_id: The joint account reference, if any.

    Raises:
        MissingJointAccountError: When ``ownership_type`` is joint but no
            account is set.

    """
    if ownership_type is OwnershipType.JOINT and joint_account_id is None:
        raise errors.MissingJointAccountError


class FinanceTrackerBaseModel(pydantic.BaseModel):
    """Base model for finance tracker entities."""

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the item.",
        default_factory=uuid.uuid4,
    )
    user_id: Annotated[
        str,
        pydantic.Field(
            description="The ID of the user who owns the item.",
        ),
    ]
    name: Annotated[str, pydantic.Field(description="The name of the item.")] = ""
    ownership_type: Annotated[
        OwnershipType,
        pydantic.Field(
            description="Whether the item is personal or shared via a joint account.",
        ),
    ] = OwnershipType.PERSONAL
    joint_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description="The joint account this item belongs to when it is joint.",
        ),
    ] = None

    @pydantic.model_validator(mode="after")
    def _check_joint_account_id(self) -> Self:
        """Ensure a joint-owned item carries a joint account reference."""
        require_joint_account_id(self.ownership_type, self.joint_account_id)
        return self


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
    linked_payment_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The payment this one settles, if any."),
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


class JointAccountModel(pydantic.BaseModel):
    """Model representing a joint (shared) account.

    Not a ``FinanceTrackerBaseModel``: a joint account has no single owning
    user and is itself the target of ``joint_account_id``, so it carries
    neither ``user_id`` nor the ownership dimension.
    """

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the joint account.",
        default_factory=uuid.uuid4,
    )
    name: Annotated[
        str,
        pydantic.Field(description="The name of the joint account.", min_length=1),
    ]


class JointAccountMemberModel(pydantic.BaseModel):
    """Model linking a user to a joint account they belong to."""

    id: uuid.UUID = pydantic.Field(
        description="The unique identifier for the membership row.",
        default_factory=uuid.uuid4,
    )
    joint_account_id: Annotated[
        uuid.UUID,
        pydantic.Field(description="The joint account the user is a member of."),
    ]
    user_id: Annotated[
        str,
        pydantic.Field(description="The ID of the member."),
    ]


class BackendUpdates(pydantic.BaseModel):
    """Model for tracking pending creates, edits and deletes before committing."""

    added_rows: list[JsonDict] = pydantic.Field(
        default_factory=list,
        description="List of new row data entries.",
    )
    edited_rows: dict[str, JsonDict] = pydantic.Field(
        default_factory=dict,
        description="Dictionary of IDs to updated row data.",
    )
    deleted_rows: list[str] = pydantic.Field(
        default_factory=list,
        description="List of row ids to be deleted.",
    )


# Union type used wherever a payment row could be either kind.
AnyPaymentModel = Annotated[
    ExpensePaymentModel | IncomePaymentModel,
    "A payment that is either an expense or income entry.",
]
