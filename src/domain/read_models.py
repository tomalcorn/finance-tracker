"""Frozen read models representing SQL view rows (query side of CQRS-lite).

Each model here corresponds to one view in the Supabase schema.  They carry
the view's computed columns (e.g. current_month, progress, remaining) alongside
the base writable-table columns -- columns that do not exist on the raw tables
and therefore cannot appear on the write models in entities.py.

Rules:
- All models are frozen (immutable after construction).
- No write semantics: no save(), no mutation helpers.
- No display formatting (pound, %) -- those live in the UI column config.
- No framework imports: stays in domain/.
"""

import datetime
import uuid
from typing import Annotated, Literal

import pydantic

from domain.entities import BudgetTrackerName


class _ViewBase(pydantic.BaseModel):
    """Shared base for all view read models."""

    model_config = pydantic.ConfigDict(frozen=True)

    id: uuid.UUID
    user_id: str
    name: str = ""


class BankAccountView(_ViewBase):
    """Read model for bank_accounts_view.

    Adds current_balance, computed from starting_balance plus payments.
    """

    starting_balance: float = 0.0
    current_balance: Annotated[
        float,
        pydantic.Field(description="Computed: starting_balance plus net payments."),
    ] = 0.0


class BudgetTrackerView(_ViewBase):
    """Read model for budget_tracker_view.

    Adds current_month, remaining, progress, and split -- all aggregated
    from payments routed through expense/income sources.
    """

    name: BudgetTrackerName
    total_budget: float = 0.0
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of payments in the current month."),
    ] = 0.0
    remaining: Annotated[
        float,
        pydantic.Field(description="total_budget minus current_month."),
    ] = 0.0
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of budget consumed (0-100)."),
    ] = 0.0
    split: Annotated[
        float,
        pydantic.Field(description="This tracker's share of total spend (0-100)."),
    ] = 0.0


class ExpenseSourceView(_ViewBase):
    """Read model for expense_sources_view.

    Adds current_month, remaining, progress, and split -- aggregated
    from payments against this source.
    """

    budget: float = 0.0
    budget_tracker_ids: list[uuid.UUID] | None = None
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of expense payments in the current month."),
    ] = 0.0
    remaining: Annotated[
        float,
        pydantic.Field(description="budget minus current_month."),
    ] = 0.0
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of budget consumed (0-100)."),
    ] = 0.0
    split: Annotated[
        float,
        pydantic.Field(description="Share of total expense spend (0-100)."),
    ] = 0.0


class IncomeSourceView(_ViewBase):
    """Read model for income_sources_view.

    Adds current_month -- the sum of income payments routed through
    this source in the current month.
    """

    budget_tracker_ids: list[uuid.UUID] = pydantic.Field(default_factory=list)
    current_month: Annotated[
        float,
        pydantic.Field(description="Sum of income payments in the current month."),
    ] = 0.0


class SubscriptionView(_ViewBase):
    """Read model for subscriptions_view.

    Adds monthly_cost -- the per-cadence amount normalised to a monthly figure.
    """

    amount: float = 0.0
    cadence: Literal["weekly", "monthly", "quarterly", "biannually", "yearly"] = (
        "monthly"
    )
    bank_account_id: uuid.UUID
    expense_source_id: uuid.UUID | None = None
    start_date: datetime.date = pydantic.Field(
        default_factory=datetime.date.today,
    )
    end_date: datetime.date | None = None
    is_active: bool = True
    monthly_cost: Annotated[
        float,
        pydantic.Field(description="amount normalised to a monthly equivalent."),
    ] = 0.0


class OneOffView(_ViewBase):
    """Read model for one_offs_view.

    Adds remaining, progress, and split -- computed from cost, banked,
    and current_month across all one-off items.
    """

    cost: float = 0.0
    current_month: float = 0.0
    banked: float = 0.0
    budget_tracker_id: uuid.UUID | None = None
    remaining: Annotated[
        float,
        pydantic.Field(description="cost minus banked."),
    ] = 0.0
    progress: Annotated[
        float,
        pydantic.Field(description="Percentage of cost banked (0-100)."),
    ] = 0.0
    split: Annotated[
        float,
        pydantic.Field(description="Share of total one-off spend (0-100)."),
    ] = 0.0
