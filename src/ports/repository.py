"""Abstract repository ports for all domain aggregates.

These interfaces define what the application *needs* from persistence.
"""

import abc
import uuid

from domain import entities


class BankAccountRepository(abc.ABC):
    """Port for bank account persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.BankAccountModel]:
        """Return all bank accounts for the current user."""

    @abc.abstractmethod
    def get_by_id(self, account_id: uuid.UUID) -> entities.BankAccountModel | None:
        """Return a single bank account, or None if not found."""

    @abc.abstractmethod
    def save(self, account: entities.BankAccountModel) -> None:
        """Insert or update a bank account record."""

    @abc.abstractmethod
    def delete(self, account_id: uuid.UUID) -> None:
        """Delete a bank account by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class BudgetTrackerRepository(abc.ABC):
    """Port for budget tracker item persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.BudgetTrackerItemModel]:
        """Return all budget tracker items for the current user."""

    @abc.abstractmethod
    def get_by_id(self, item_id: uuid.UUID) -> entities.BudgetTrackerItemModel | None:
        """Return a single budget tracker item, or None if not found."""

    @abc.abstractmethod
    def get_by_ids(
        self,
        item_ids: list[uuid.UUID],
    ) -> list[entities.BudgetTrackerItemModel]:
        """Return budget tracker items matching the given IDs."""

    @abc.abstractmethod
    def save(self, item: entities.BudgetTrackerItemModel) -> None:
        """Insert or update a budget tracker item."""

    @abc.abstractmethod
    def save_many(self, items: list[entities.BudgetTrackerItemModel]) -> None:
        """Insert or update multiple budget tracker items in one operation.

        Used by InitializeUserWorkspaceUseCase to seed default trackers.
        """

    @abc.abstractmethod
    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a budget tracker item by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class ExpenseSourceRepository(abc.ABC):
    """Port for expense source persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.ExpenseSourceModel]:
        """Return all expense sources for the current user."""

    @abc.abstractmethod
    def get_by_id(self, source_id: uuid.UUID) -> entities.ExpenseSourceModel | None:
        """Return a single expense source, or None if not found."""

    @abc.abstractmethod
    def save(self, source: entities.ExpenseSourceModel) -> None:
        """Insert or update an expense source."""

    @abc.abstractmethod
    def delete(self, source_id: uuid.UUID) -> None:
        """Delete an expense source by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class IncomeSourceRepository(abc.ABC):
    """Port for income source persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.IncomeSourceModel]:
        """Return all income sources for the current user."""

    @abc.abstractmethod
    def get_by_id(self, source_id: uuid.UUID) -> entities.IncomeSourceModel | None:
        """Return a single income source, or None if not found."""

    @abc.abstractmethod
    def save(self, source: entities.IncomeSourceModel) -> None:
        """Insert or update an income source."""

    @abc.abstractmethod
    def delete(self, source_id: uuid.UUID) -> None:
        """Delete an income source by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class OneOffRepository(abc.ABC):
    """Port for one-off savings goal item persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.OneOffItemModel]:
        """Return all one-off items for the current user."""

    @abc.abstractmethod
    def get_by_id(self, item_id: uuid.UUID) -> entities.OneOffItemModel | None:
        """Return a single one-off item, or None if not found."""

    @abc.abstractmethod
    def get_by_ids(self, item_ids: list[uuid.UUID]) -> list[entities.OneOffItemModel]:
        """Return one-off items matching the given IDs.

        Used by BankOneOffsUseCase to load only the selected items.
        """

    @abc.abstractmethod
    def save(self, item: entities.OneOffItemModel) -> None:
        """Insert or update a one-off item."""

    @abc.abstractmethod
    def delete(self, item_id: uuid.UUID) -> None:
        """Delete a one-off item by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class SubscriptionRepository(abc.ABC):
    """Port for subscription persistence."""

    @abc.abstractmethod
    def get_all(self) -> list[entities.SubscriptionModel]:
        """Return all subscriptions for the current user."""

    @abc.abstractmethod
    def get_active(self) -> list[entities.SubscriptionModel]:
        """Return only active subscriptions (is_active=True) for the current user.

        Used by ReconcileSubscriptionsUseCase to find subscriptions that
        may need future payments created.
        """

    @abc.abstractmethod
    def get_by_id(
        self,
        subscription_id: uuid.UUID,
    ) -> entities.SubscriptionModel | None:
        """Return a single subscription, or None if not found."""

    @abc.abstractmethod
    def save(self, subscription: entities.SubscriptionModel) -> None:
        """Insert or update a subscription."""

    @abc.abstractmethod
    def delete(self, subscription_id: uuid.UUID) -> None:
        """Delete a subscription by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""


class PaymentRepository(abc.ABC):
    """Port for payment persistence.

    Handles both ExpensePaymentModel and IncomePaymentModel. The concrete
    implementation is responsible for mapping the payment_type discriminator
    to the correct table or row format.
    """

    @abc.abstractmethod
    def get_all(self) -> list[entities.AnyPaymentModel]:
        """Return all payments (expense and income) for the current user."""

    @abc.abstractmethod
    def get_by_bank_account(
        self,
        bank_account_id: uuid.UUID,
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments associated with a specific bank account.

        Used when banking one-offs to find existing payments for the account.
        """

    @abc.abstractmethod
    def get_by_subscription(
        self,
        subscription_id: uuid.UUID,
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments generated from a specific subscription.

        Used by ReconcileSubscriptionsUseCase to determine whether future
        payments already exist.
        """

    @abc.abstractmethod
    def save(self, payment: entities.AnyPaymentModel) -> None:
        """Insert or update a single payment."""

    @abc.abstractmethod
    def save_many(self, payments: list[entities.AnyPaymentModel]) -> None:
        """Insert or update multiple payments in one operation.

        Used by ReconcileSubscriptionsUseCase to bulk-create future payments.
        """

    @abc.abstractmethod
    def apply_updates(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of payment inserts and deletes in one operation.

        Used by ReconcileSubscriptionsUseCase to persist reconciliation
        changes atomically and invalidate dependent view caches.
        """

    @abc.abstractmethod
    def delete(self, payment_id: uuid.UUID) -> None:
        """Delete a payment by ID."""

    @abc.abstractmethod
    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""
