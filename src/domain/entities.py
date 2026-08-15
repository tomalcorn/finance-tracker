"""Pure domain entities for backend data."""

import datetime
import enum
import uuid
from collections.abc import Mapping, Sequence
from typing import Annotated, Literal, Protocol, Self, runtime_checkable

import pydantic

from domain import errors

type JSON = None | bool | str | int | float | Sequence[JSON] | Mapping[str, JSON]
type JsonDict = dict[str, JSON]

type RawRow = Mapping[str, object]
"""An unvalidated field map on its way into an entity."""


class OwnershipType(enum.StrEnum):
    """Whether an aggregate belongs to one user or a shared joint account."""

    PERSONAL = enum.auto()
    JOINT = enum.auto()


@runtime_checkable
class HasOwnershipDimension(Protocol):
    """An entity that is owned personally or by a joint account.

    The joint tables have no ownership dimension, so their entities do not
    satisfy this: whether ownership applies to an aggregate is a question about
    the entity, not about the caller inspecting it.
    """

    ownership_type: OwnershipType
    joint_account_id: uuid.UUID | None


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

    # revalidate_instances: model_copy(update=...) skips field validators, so a
    # modified copy is re-validated by passing it back through model_validate.
    # Without this, validating an existing instance returns it untouched.
    model_config = pydantic.ConfigDict(frozen=True, revalidate_instances="always")

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


class CategoryModel(FinanceTrackerBaseModel):
    """Model representing a category money can be attributed to.

    Categories are a two-level tree. A **root** (``parent_id is None``) is one of
    the fixed :class:`BudgetTrackerName` names and is seeded, not created; its
    **children** are the user's own subcategories. A payment may be attributed to
    either level, so ``budget`` is the same number at both: what this category is
    allowed, whether or not it has children.

    Depth is enforced in the database — a category cannot see its siblings from
    here, so only the self-parent half of the rule is checkable on the entity.
    """

    parent_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description="The category this one sits under; None for a root.",
        ),
    ] = None
    budget: Annotated[
        float,
        pydantic.Field(description="What this category is allowed each month."),
    ] = 0.0

    @property
    def is_root(self) -> bool:
        """Whether this is a top-level category rather than a subcategory."""
        return self.parent_id is None

    @pydantic.model_validator(mode="after")
    def _check_not_self_parented(self) -> Self:
        """Reject a category that names itself as its parent.

        Raises:
            SelfParentedCategoryError: The category is its own parent, which
                would put it in a cycle of one.

        """
        if self.parent_id is not None and self.parent_id == self.id:
            raise errors.SelfParentedCategoryError(self.name)
        return self


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
    """Model representing a recurring subscription.

    A subscription with ``joint_income_source_id`` set is a *joint
    contribution*: a standing instruction that books a linked pair of payments
    each cadence — the personal expense every subscription books, plus a
    matching income owned by the joint account. The two joint fields are the
    income leg's own source and destination account, so they are set together or
    not at all.
    """

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
    joint_income_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description=(
                "The joint income source the contribution's income leg is booked "
                "against. Set means this subscription is a joint contribution."
            ),
        ),
    ] = None
    joint_bank_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(
            description="The joint bank account the contribution arrives in.",
        ),
    ] = None

    @property
    def is_joint_contribution(self) -> bool:
        """Whether each cadence books a joint contribution as well as an expense."""
        return self.joint_income_source_id is not None

    @pydantic.model_validator(mode="after")
    def _check_joint_contribution(self) -> Self:
        """Ensure a contribution is complete, and is one a personal row may book.

        Raises:
            IncompleteJointContributionError: A joint field is set without the
                other, so the income leg could not be written.
            JointOwnedContributionError: A joint-owned subscription claims to be
                a contribution. Only the personal side contributes; a joint row
                doing so would book an expense with no counterpart.

        """
        joint_fields = {
            "joint_income_source_id": self.joint_income_source_id,
            "joint_bank_account_id": self.joint_bank_account_id,
        }
        missing = [field for field, value in joint_fields.items() if value is None]
        if missing and len(missing) < len(joint_fields):
            raise errors.IncompleteJointContributionError(self.name, missing)
        if self.is_joint_contribution and self.ownership_type is OwnershipType.JOINT:
            raise errors.JointOwnedContributionError(self.name)
        return self


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


class QuickButtonMode(enum.StrEnum):
    """What tapping a quick button does."""

    LOG = enum.auto()
    """Log the preset immediately."""

    PROMPT = enum.auto()
    """Open a payment form pre-filled with whatever the preset holds."""


class QuickButtonModel(FinanceTrackerBaseModel):
    """Model representing a preset expense behind a quick-entry button.

    Two things are named here, and they are not the same thing. ``name`` labels
    the *button* and is always required — a tile has to say what it is. The
    payment fields below are the preset it fills a payment in with, and are
    optional, because a ``PROMPT`` button exists precisely to leave the varying
    parts blank until it is tapped. A ``LOG`` button has no such second chance,
    so the fields a payment cannot be written without are required of it — see
    :meth:`_check_loggable`.

    The preset amount may be negative, which logs money coming back rather than
    going out. Zero is the one amount refused: it would log a payment that moves
    nothing.
    """

    name: Annotated[
        str,
        pydantic.Field(description="The label shown on the button.", min_length=1),
    ]
    payment_name: Annotated[
        str | None,
        pydantic.Field(
            description=(
                "The name to log the payment under. Defaults to the button's own "
                "label when unset."
            ),
        ),
    ] = None
    mode: Annotated[
        QuickButtonMode,
        pydantic.Field(description="Whether a tap logs the preset or asks first."),
    ] = QuickButtonMode.LOG
    expense: Annotated[
        float | None,
        pydantic.Field(
            description=(
                "The expense amount a tap logs. Negative for a button that logs "
                "money coming back, such as a recurring reimbursement."
            ),
        ),
    ] = None
    bank_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The bank account the payment comes from."),
    ] = None
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The expense source the payment is booked to."),
    ] = None
    icon: Annotated[
        str | None,
        pydantic.Field(description="An optional emoji shown before the name."),
    ] = None
    display_order: Annotated[
        pydantic.NonNegativeInt,
        pydantic.Field(description="Position of the button in the grid."),
    ] = 0

    @pydantic.model_validator(mode="after")
    def _check_loggable(self) -> Self:
        """Ensure a one-tap button holds everything a payment needs.

        Raises:
            IncompleteQuickButtonError: The button logs on tap but is missing a
                field the payment cannot be written without.

        """
        if self.mode is not QuickButtonMode.LOG:
            return self
        missing = [
            field
            for field, value in (
                ("expense", self.expense),
                ("bank_account_id", self.bank_account_id),
            )
            if value is None
        ]
        if missing:
            raise errors.IncompleteQuickButtonError(self.name, missing)
        return self

    @pydantic.model_validator(mode="after")
    def _check_amount_moves_money(self) -> Self:
        """Reject a preset amount of zero, in either mode.

        A field constraint cannot say "anything but zero", and the old ``gt=0``
        said too much: it also ruled out the negative a reimbursement button needs.

        Raises:
            ZeroQuickButtonAmountError: The button presets an amount of zero.

        """
        if self.expense == 0:
            raise errors.ZeroQuickButtonAmountError(self.name)
        return self


class IncomeRollUpPeriod(enum.StrEnum):
    """Which month's income payments an income source totals up.

    The expense side is always the current month; this moves only the income
    window, so ``PREVIOUS_MONTH`` means "budget this month against last month's
    pay" — the shape of it for anyone paid at the end of the month.
    """

    CURRENT_MONTH = enum.auto()
    PREVIOUS_MONTH = enum.auto()


class UserSettingsModel(FinanceTrackerBaseModel):
    """Model representing the preferences for one half of a user's finances.

    One row per configurable scope, not per user: ``PERSONAL`` settings belong
    to the user, ``JOINT`` settings to the account they share, so the two halves
    are configured independently. ``name`` is inherited but unused — a settings
    row is not a named thing — and stays empty.
    """

    income_roll_up_period: Annotated[
        IncomeRollUpPeriod,
        pydantic.Field(
            description="The month income sources total their payments over.",
        ),
    ] = IncomeRollUpPeriod.CURRENT_MONTH


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


type EditedRows = dict[str, JsonDict]
type DeletedIds = list[str]


# Union type used wherever a payment row could be either kind.
AnyPaymentModel = Annotated[
    ExpensePaymentModel | IncomePaymentModel,
    "A payment that is either an expense or income entry.",
]
