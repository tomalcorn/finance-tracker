"""Abstract repository ports for all domain aggregates.

These interfaces define what the application *needs* from persistence.
Concrete implementations (Supabase, in-memory fakes) live in adapters/.

No I/O, no Supabase imports, no Streamlit here.
"""

import abc
import uuid
from typing import Annotated

from domain.entities import (
    BankAccountModel,
    BudgetTrackerItemModel,
    ExpensePaymentModel,
    ExpenseSourceModel,
    IncomePaymentModel,
    IncomeSourceModel,
    OneOffItemModel,
    SubscriptionModel,
)

# Union type used wherever a payment row could be either kind.
AnyPaymentModel = Annotated[
    ExpensePaymentModel | IncomePaymentModel,
    "A payment that is either an expense or income entry.",
]


class BankAccountRepository(abc.ABC):
    """Port for bank account persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[BankAccountModel]:
        """Return all bank accounts belonging to the given user."""

    @abc.abstractmethod
    def get_by_id(self, account_id: uuid.UUID) -> BankAccountModel | None:
        """Return a single bank account, or None if not found."""

    @abc.abstractmethod
    def save(self, account: BankAccountModel) -> None:
        """Insert or update a bank account record."""

    @abc.abstractmethod
    def delete(self, account_id: uuid.UUID) -> None:
        """Delete a bank account by ID."""


class BudgetTrackerRepository(abc.ABC):
    """Port for budget tracker item persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[BudgetTrackerItemModel]:
        """Return all budget tracker items belonging to the given user."""

    @abc.abstractmethod
    def get_by_id(self, item_id: uuid.UUID) -> BudgetTrackerItemModel | None:
        """Return a single budget tracker item, or None if not found."""

    @abc.abstractmethod
    def get_by_ids(self, item_ids: list[uuid.UUID]) -> list[BudgetTrackerItemModel]:
        """Return budget tracker items matching the given IDs."""

    @abc.abstractmethod
    def save(self, item: BudgetTrackerItemModel) -> None:
        """Insert or update a budget tracker item."""

    @abc.abstractmethod
    def save_many(self, items: list[BudgetTrackerItemModel]) -> None:
        """Insert or update multiple budget tracker items in one operation.

        Used by InitializeUserWorkspaceUseCase to seed default trackers.
        """

    @abc.abstractmethod
    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a budget tracker item by ID."""


class ExpenseSourceRepository(abc.ABC):
    """Port for expense source persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[ExpenseSourceModel]:
        """Return all expense sources belonging to the given user."""

    @abc.abstractmethod
    def get_by_id(self, source_id: uuid.UUID) -> ExpenseSourceModel | None:
        """Return a single expense source, or None if not found."""

    @abc.abstractmethod
    def save(self, source: ExpenseSourceModel) -> None:
        """Insert or update an expense source."""

    @abc.abstractmethod
    def delete(self, source_id: uuid.UUID) -> None:
        """Delete an expense source by ID."""


class IncomeSourceRepository(abc.ABC):
    """Port for income source persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[IncomeSourceModel]:
        """Return all income sources belonging to the given user."""

    @abc.abstractmethod
    def get_by_id(self, source_id: uuid.UUID) -> IncomeSourceModel | None:
        """Return a single income source, or None if not found."""

    @abc.abstractmethod
    def save(self, source: IncomeSourceModel) -> None:
        """Insert or update an income source."""

    @abc.abstractmethod
    def delete(self, source_id: uuid.UUID) -> None:
        """Delete an income source by ID."""


class OneOffRepository(abc.ABC):
    """Port for one-off savings goal item persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[OneOffItemModel]:
        """Return all one-off items belonging to the given user."""

    @abc.abstractmethod
    def get_by_id(self, item_id: uuid.UUID) -> OneOffItemModel | None:
        """Return a single one-off item, or None if not found."""

    @abc.abstractmethod
    def get_by_ids(self, item_ids: list[uuid.UUID]) -> list[OneOffItemModel]:
        """Return one-off items matching the given IDs.

        Used by BankOneOffsUseCase to load only the selected items.
        """

    @abc.abstractmethod
    def save(self, item: OneOffItemModel) -> None:
        """Insert or update a one-off item."""

    @abc.abstractmethod
    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a one-off item by ID."""


class SubscriptionRepository(abc.ABC):
    """Port for subscription persistence."""

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[SubscriptionModel]:
        """Return all subscriptions belonging to the given user."""

    @abc.abstractmethod
    def get_active(self, *, user_id: str) -> list[SubscriptionModel]:
        """Return only active subscriptions (is_active=True).

        Used by ReconcileSubscriptionsUseCase to find subscriptions that
        may need future payments created.
        """

    @abc.abstractmethod
    def get_by_id(self, subscription_id: uuid.UUID) -> SubscriptionModel | None:
        """Return a single subscription, or None if not found."""

    @abc.abstractmethod
    def save(self, subscription: SubscriptionModel) -> None:
        """Insert or update a subscription."""

    @abc.abstractmethod
    def delete(self, subscription_id: uuid.UUID) -> None:
        """Delete a subscription by ID."""


class PaymentRepository(abc.ABC):
    """Port for payment persistence.

    Handles both ExpensePaymentModel and IncomePaymentModel. The concrete
    implementation is responsible for mapping the payment_type discriminator
    to the correct table or row format.
    """

    @abc.abstractmethod
    def get_all(self, *, user_id: str) -> list[AnyPaymentModel]:
        """Return all payments (expense and income) for the given user."""

    @abc.abstractmethod
    def get_by_bank_account(
        self,
        bank_account_id: uuid.UUID,
    ) -> list[AnyPaymentModel]:
        """Return all payments associated with a specific bank account.

        Used when banking one-offs to find existing payments for the account.
        """

    @abc.abstractmethod
    def get_by_subscription(
        self,
        subscription_id: uuid.UUID,
    ) -> list[AnyPaymentModel]:
        """Return all payments generated from a specific subscription.

        Used by ReconcileSubscriptionsUseCase to determine whether future
        payments already exist.
        """

    @abc.abstractmethod
    def save(self, payment: AnyPaymentModel) -> None:
        """Insert or update a single payment."""

    @abc.abstractmethod
    def save_many(self, payments: list[AnyPaymentModel]) -> None:
        """Insert or update multiple payments in one operation.

        Used by ReconcileSubscriptionsUseCase to bulk-create future payments.
        """

    @abc.abstractmethod
    def delete(self, payment_id: uuid.UUID) -> None:
        """Delete a payment by ID."""
