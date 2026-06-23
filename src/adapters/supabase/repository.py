"""Concrete Supabase implementations of the repository ports.

Each class wraps client calls and translates low-level exceptions
into AdapterError so the use-case layer never sees Supabase internals.

Imports of client and st_supabase_connection are intentionally
confined to this file (and adapters/supabase/ generally).
"""

from typing import TYPE_CHECKING

import pydantic

from adapters import cache as cache_mod
from adapters import errors
from adapters.supabase import client, table_names
from domain import entities
from ports import repository

if TYPE_CHECKING:
    import uuid

    import st_supabase_connection

# TypeAdapter for deserialising payment rows into the correct subtype
# using the payment_type discriminator field.
_PaymentAdapter = pydantic.TypeAdapter(entities.AnyPaymentModel)


def _parse_payment(row: dict) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


class SupabaseRepositoryBase:
    """Shared infrastructure for all Supabase repository implementations.

    Subclasses receive a connection, user_id, and the read/write table names
    at construction time. The protected helpers below handle the repetitive
    parts of every CRUD operation — data fetching, error wrapping, and cache
    invalidation — so subclasses only need to call model_validate on the
    returned rows.
    """

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        read_table: table_names.ViewNames | table_names.TableNames,
        write_table: table_names.TableNames,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection, user scope, and table names.

        Args:
            connection: The Supabase connection to use for all queries.
            user_id: The authenticated user's ID. All reads are scoped to
                this user; callers must not pass rows belonging to other users.
            read_table: The view or table to query for reads. Views are
                preferred where they exist as they include computed fields.
            write_table: The raw table to target for inserts, updates, and
                deletes. Must not be a view.
            cache: A CacheGateway that owns both cached reads and
                write-with-invalidation, injected from the composition layer.
                When omitted (e.g. in unit tests) reads and writes go directly
                to the Supabase client, uncached.

        """
        self._conn = connection
        self._user_id = user_id
        self._read_table = read_table
        self._write_table = write_table
        self._cache = cache

    def _fetch_rows(self) -> list[dict]:
        """Fetch all rows for the current user from the read table.

        Raises:
            AdapterError: If the underlying client call fails for
                any reason (network, Supabase HTTP error, etc.).

        """
        try:
            if self._cache is not None:
                rows = self._cache.fetch(self._read_table)
            else:
                rows = client.fetch_table(self._read_table, "*", [], self._conn)
            return [r for r in rows if r["user_id"] == self._user_id]
        except Exception as e:
            msg = f"Failed to fetch rows from {self._read_table}: {e}"
            raise errors.AdapterError(msg) from e

    def _fetch_by_id(self, row_id: "uuid.UUID") -> dict | None:
        """Fetch a single row by ID, or return None if not found.

        Filters in Python over the cached result of _fetch_rows, so this
        is cheap when the cache is warm.

        Raises:
            AdapterError: If the underlying fetch fails.

        """
        rows = self._fetch_rows()
        matches = [r for r in rows if r["id"] == str(row_id)]
        return matches[0] if matches else None

    def _fetch_by_ids(self, row_ids: list["uuid.UUID"]) -> list[dict]:
        """Fetch multiple rows by ID.

        Filters in Python over the cached result of _fetch_rows. Order of
        results is not guaranteed to match the order of row_ids.

        Raises:
            AdapterError: If the underlying fetch fails.

        """
        id_strs = {str(i) for i in row_ids}
        rows = self._fetch_rows()
        return [r for r in rows if r["id"] in id_strs]

    def _write(self, updates: entities.BackendUpdates, error_context: str) -> None:
        """Apply updates to the write table, routing through the cache if present.

        The single funnel for every write. When a CacheGateway is injected the
        write goes through it, so the matching cached reads are invalidated in
        the same call; otherwise it falls back to a direct client write (used
        in tests and by not-yet-migrated repositories).

        Args:
            updates: The inserts/edits/deletes to apply.
            error_context: Human-readable prefix for the AdapterError raised on
                failure (e.g. "Failed to save row to payments").

        Raises:
            AdapterError: If the underlying write fails.

        """
        try:
            if self._cache is not None:
                self._cache.write(self._write_table, updates)
            else:
                client.update_backend(
                    self._write_table,
                    updates,
                    connection=self._conn,
                )
        except Exception as e:
            msg = f"{error_context}: {e}"
            raise errors.AdapterError(msg) from e

    def _save_one(self, row: dict) -> None:
        """Insert or update a single row in the write table.

        Relies on Supabase upsert semantics — the table must have an
        ON CONFLICT DO UPDATE policy on the id column.

        Raises:
            AdapterError: If the write fails.

        """
        self._write(
            entities.BackendUpdates(added_rows=[row]),
            f"Failed to save row to {self._write_table}",
        )

    def _save_many(self, rows: list[dict]) -> None:
        """Insert multiple rows in a single batch operation.

        All rows are sent as a single insert. Relies on Supabase upsert
        semantics if any rows already exist.

        Raises:
            AdapterError: If the write fails.

        """
        self._write(
            entities.BackendUpdates(added_rows=rows),
            f"Failed to bulk-save rows to {self._write_table}",
        )

    def _delete_by_id(self, row_id: "uuid.UUID") -> None:
        """Delete a single row by ID from the write table.

        Raises:
            AdapterError: If the write fails.

        """
        self._write(
            entities.BackendUpdates(deleted_rows=[str(row_id)]),
            f"Failed to delete row {row_id} from {self._write_table}",
        )

    def get_column_values(self, column_name: str) -> set[object]:
        """Return a set of unique column values for a column."""
        return {row[column_name] for row in self._fetch_rows() if column_name in row}

    def get_rows(self) -> list[dict]:
        """Return the raw user-scoped rows from the read view.

        Unlike ``get_all`` this skips domain-model validation, so view-only
        computed columns (e.g. progress, remaining) survive for the grid to
        display. Used by the UI grid data source under Path A.
        """
        return self._fetch_rows()


class SupabaseBankAccountRepository(
    SupabaseRepositoryBase,
    repository.BankAccountRepository,
):
    """Supabase implementation of BankAccountRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.BANK_ACCOUNTS,
            write_table=table_names.TableNames.BANK_ACCOUNTS,
            cache=cache,
        )

    def get_all(self) -> list[entities.BankAccountModel]:
        """Return all bank accounts for the current user."""
        return [entities.BankAccountModel.model_validate(r) for r in self._fetch_rows()]

    def get_by_id(self, account_id: "uuid.UUID") -> entities.BankAccountModel | None:
        """Return a single bank account by ID, or None if not found."""
        row = self._fetch_by_id(account_id)
        return entities.BankAccountModel.model_validate(row) if row else None

    def save(self, account: entities.BankAccountModel) -> None:
        """Insert or update a bank account record."""
        self._save_one(account.model_dump(mode="json"))

    def delete(self, account_id: "uuid.UUID") -> None:
        """Delete a bank account by ID."""
        self._delete_by_id(account_id)


# ---------------------------------------------------------------------------
# Budget tracker items
# ---------------------------------------------------------------------------


class SupabaseBudgetTrackerRepository(
    SupabaseRepositoryBase,
    repository.BudgetTrackerRepository,
):
    """Supabase implementation of BudgetTrackerRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.BUDGET_TRACKER,
            write_table=table_names.TableNames.BUDGET_TRACKER,
            cache=cache,
        )

    def get_all(self) -> list[entities.BudgetTrackerItemModel]:
        """Return all budget tracker items for the current user."""
        return [
            entities.BudgetTrackerItemModel.model_validate(r)
            for r in self._fetch_rows()
        ]

    def get_by_id(self, item_id: "uuid.UUID") -> entities.BudgetTrackerItemModel | None:
        """Return a single budget tracker item by ID, or None if not found."""
        row = self._fetch_by_id(item_id)
        return entities.BudgetTrackerItemModel.model_validate(row) if row else None

    def get_by_ids(
        self,
        item_ids: list["uuid.UUID"],
    ) -> list[entities.BudgetTrackerItemModel]:
        """Return budget tracker items matching the given IDs."""
        return [
            entities.BudgetTrackerItemModel.model_validate(r)
            for r in self._fetch_by_ids(item_ids)
        ]

    def save(self, item: entities.BudgetTrackerItemModel) -> None:
        """Insert or update a single budget tracker item."""
        self._save_one(item.model_dump(mode="json"))

    def save_many(self, items: list[entities.BudgetTrackerItemModel]) -> None:
        """Insert multiple budget tracker items in a single batch.

        Used by InitializeUserWorkspaceUseCase to seed default trackers
        for a new user.
        """
        self._save_many([i.model_dump(mode="json") for i in items])

    def delete(self, item_id: "uuid.UUID") -> None:
        """Delete a budget tracker item by ID."""
        self._delete_by_id(item_id)


# ---------------------------------------------------------------------------
# Expense sources
# ---------------------------------------------------------------------------


class SupabaseExpenseSourceRepository(
    SupabaseRepositoryBase,
    repository.ExpenseSourceRepository,
):
    """Supabase implementation of ExpenseSourceRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.EXPENSE_SOURCES,
            write_table=table_names.TableNames.EXPENSE_SOURCES,
            cache=cache,
        )

    def get_all(self) -> list[entities.ExpenseSourceModel]:
        """Return all expense sources for the current user."""
        return [
            entities.ExpenseSourceModel.model_validate(r) for r in self._fetch_rows()
        ]

    def get_by_id(self, source_id: "uuid.UUID") -> entities.ExpenseSourceModel | None:
        """Return a single expense source by ID, or None if not found."""
        row = self._fetch_by_id(source_id)
        return entities.ExpenseSourceModel.model_validate(row) if row else None

    def save(self, source: entities.ExpenseSourceModel) -> None:
        """Insert or update an expense source record."""
        self._save_one(source.model_dump(mode="json"))

    def delete(self, source_id: "uuid.UUID") -> None:
        """Delete an expense source by ID."""
        self._delete_by_id(source_id)


# ---------------------------------------------------------------------------
# Income sources
# ---------------------------------------------------------------------------


class SupabaseIncomeSourceRepository(
    SupabaseRepositoryBase,
    repository.IncomeSourceRepository,
):
    """Supabase implementation of IncomeSourceRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.INCOME_SOURCES,
            write_table=table_names.TableNames.INCOME_SOURCES,
            cache=cache,
        )

    def get_all(self) -> list[entities.IncomeSourceModel]:
        """Return all income sources for the current user."""
        return [
            entities.IncomeSourceModel.model_validate(r) for r in self._fetch_rows()
        ]

    def get_by_id(self, source_id: "uuid.UUID") -> entities.IncomeSourceModel | None:
        """Return a single income source by ID, or None if not found."""
        row = self._fetch_by_id(source_id)
        return entities.IncomeSourceModel.model_validate(row) if row else None

    def save(self, source: entities.IncomeSourceModel) -> None:
        """Insert or update an income source record."""
        self._save_one(source.model_dump(mode="json"))

    def delete(self, source_id: "uuid.UUID") -> None:
        """Delete an income source by ID."""
        self._delete_by_id(source_id)


# ---------------------------------------------------------------------------
# One-off items
# ---------------------------------------------------------------------------


class SupabaseOneOffRepository(
    SupabaseRepositoryBase,
    repository.OneOffRepository,
):
    """Supabase implementation of OneOffRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.ONE_OFFS,
            write_table=table_names.TableNames.ONE_OFFS,
            cache=cache,
        )

    def get_all(self) -> list[entities.OneOffItemModel]:
        """Return all one-off items for the current user."""
        return [entities.OneOffItemModel.model_validate(r) for r in self._fetch_rows()]

    def get_by_id(self, item_id: "uuid.UUID") -> entities.OneOffItemModel | None:
        """Return a single one-off item by ID, or None if not found."""
        row = self._fetch_by_id(item_id)
        return entities.OneOffItemModel.model_validate(row) if row else None

    def get_by_ids(self, item_ids: list["uuid.UUID"]) -> list[entities.OneOffItemModel]:
        """Return one-off items matching the given IDs.

        Used by BankOneOffsUseCase to load only the items selected by the user.
        """
        return [
            entities.OneOffItemModel.model_validate(r)
            for r in self._fetch_by_ids(item_ids)
        ]

    def save(self, item: entities.OneOffItemModel) -> None:
        """Insert or update a one-off item record."""
        self._save_one(item.model_dump(mode="json"))

    def delete(self, item_id: "uuid.UUID") -> None:
        """Delete a one-off item by ID."""
        self._delete_by_id(item_id)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


class SupabaseSubscriptionRepository(
    SupabaseRepositoryBase,
    repository.SubscriptionRepository,
):
    """Supabase implementation of SubscriptionRepository."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.ViewNames.SUBSCRIPTIONS,
            write_table=table_names.TableNames.SUBSCRIPTIONS,
            cache=cache,
        )

    def get_all(self) -> list[entities.SubscriptionModel]:
        """Return all subscriptions for the current user."""
        return [
            entities.SubscriptionModel.model_validate(r) for r in self._fetch_rows()
        ]

    def get_active(self) -> list[entities.SubscriptionModel]:
        """Return only active subscriptions (is_active=True) for the current user.

        Used by ReconcileSubscriptionsUseCase to find subscriptions that
        may need future payments created.
        """
        return [s for s in self.get_all() if s.is_active]

    def get_by_id(
        self,
        subscription_id: "uuid.UUID",
    ) -> entities.SubscriptionModel | None:
        """Return a single subscription by ID, or None if not found."""
        row = self._fetch_by_id(subscription_id)
        return entities.SubscriptionModel.model_validate(row) if row else None

    def save(self, subscription: entities.SubscriptionModel) -> None:
        """Insert or update a subscription record."""
        self._save_one(subscription.model_dump(mode="json"))

    def delete(self, subscription_id: "uuid.UUID") -> None:
        """Delete a subscription by ID."""
        self._delete_by_id(subscription_id)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class SupabasePaymentRepository(
    SupabaseRepositoryBase,
    repository.PaymentRepository,
):
    """Supabase implementation of PaymentRepository.

    Payments have no view — reads go directly to the raw table. The
    payment_type discriminator field is used to deserialise each row
    into either ExpensePaymentModel or IncomePaymentModel.
    """

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        user_id: str,
        cache: cache_mod.CacheGateway | None = None,
    ) -> None:
        """Initialise with a Supabase connection and user scope."""
        super().__init__(
            connection=connection,
            user_id=user_id,
            read_table=table_names.TableNames.PAYMENTS,
            write_table=table_names.TableNames.PAYMENTS,
            cache=cache,
        )

    def get_all(self) -> list[entities.AnyPaymentModel]:
        """Return all payments for the current user."""
        return [_parse_payment(r) for r in self._fetch_rows()]

    def get_by_bank_account(
        self,
        bank_account_id: "uuid.UUID",
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments associated with a specific bank account.

        Used when banking one-offs to check for existing payments against
        the target account.
        """
        rows = self._fetch_rows()
        return [
            _parse_payment(r)
            for r in rows
            if r.get("bank_account_id") == str(bank_account_id)
        ]

    def get_by_subscription(
        self,
        subscription_id: "uuid.UUID",
    ) -> list[entities.AnyPaymentModel]:
        """Return all payments generated from a specific subscription.

        Used by ReconcileSubscriptionsUseCase to determine whether future
        payments already exist before creating new ones.
        """
        rows = self._fetch_rows()
        return [
            _parse_payment(r)
            for r in rows
            if r.get("subscription_id") == str(subscription_id)
        ]

    def save(self, payment: entities.AnyPaymentModel) -> None:
        """Insert or update a single payment record."""
        self._save_one(payment.model_dump(mode="json"))

    def save_many(self, payments: list[entities.AnyPaymentModel]) -> None:
        """Insert multiple payment records in a single batch.

        Used by ReconcileSubscriptionsUseCase to bulk-create future payments.
        """
        self._save_many([p.model_dump(mode="json") for p in payments])

    def apply_updates(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of payment inserts and deletes in one operation."""
        if (
            not updates.added_rows
            and not updates.deleted_rows
            and not updates.edited_rows
        ):
            return
        self._write(
            updates,
            f"Failed to apply payment updates to {self._write_table}",
        )

    def delete(self, payment_id: "uuid.UUID") -> None:
        """Delete a payment by ID."""
        self._delete_by_id(payment_id)
