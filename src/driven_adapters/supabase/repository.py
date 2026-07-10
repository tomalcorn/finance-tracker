"""Generic Supabase implementation of the repository port.

One ``SupabaseRepository`` serves every aggregate; the per-aggregate
differences (entity parser, view model, and read/write table names) are data,
supplied by the typed factory functions at the bottom of this module. The
class also structurally satisfies the UI's ``GridDataSource`` port (``rows`` /
``unique_values`` / ``apply``) so composition can hand a repository straight to
a grid with no adapter in between.

All I/O goes through the injected ``CacheGateway`` (cached reads,
write-with-invalidation); nothing here touches the Supabase client directly.
"""

from typing import TYPE_CHECKING

import pydantic

from domain import entities, read_models
from driven_adapters import cache as cache_mod
from driven_adapters import errors
from driven_adapters.supabase import table_names
from ports import repository

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable

# TypeAdapter for deserialising payment rows into the correct subtype
# using the payment_type discriminator field.
_PaymentAdapter = pydantic.TypeAdapter(entities.AnyPaymentModel)


def _parse_payment(row: dict) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


class SupabaseRepository[EntityT: pydantic.BaseModel](repository.Repository[EntityT]):
    """Generic Supabase repository for one aggregate.

    Reads go through the injected cache (which fans out to the versioned
    Streamlit cache); writes go through the cache's write-with-invalidation.
    Reads are re-scoped to ``user_id`` in Python because the cache is shared
    across sessions and keyed by table only.
    """

    def __init__(  # noqa: PLR0913 - generic repo needs its aggregate's full spec
        self,
        user_id: str,
        *,
        parse: "Callable[[dict], EntityT]",
        view_model: type[pydantic.BaseModel],
        read_table: table_names.ViewNames | table_names.TableNames,
        write_table: table_names.TableNames,
        cache: cache_mod.CacheGateway,
    ) -> None:
        """Initialise with a user scope and the aggregate's spec.

        Args:
            user_id: The authenticated user's ID. All reads are scoped to this
                user; callers must not pass rows belonging to other users.
            parse: Deserialises a raw row into the write-model entity. For most
                aggregates this is ``EntityModel.model_validate``; payments use
                the discriminated-union TypeAdapter.
            view_model: The ``domain.read_models`` view the ``rows()`` display
                read validates raw rows into.
            read_table: The view or table to query for reads.
            write_table: The raw table to target for inserts, updates, deletes.
            cache: A CacheGateway owning cached reads and
                write-with-invalidation, injected from composition.

        """
        self._user_id = user_id
        self._parse = parse
        self._view_model = view_model
        self._read_table = read_table
        self._write_table = write_table
        self._cache = cache

    # -- internal helpers ---------------------------------------------------

    def _fetch_rows(self) -> list[dict]:
        """Fetch all rows for the current user from the read table.

        Raises:
            AdapterError: If the underlying fetch fails.

        """
        try:
            rows = self._cache.fetch(self._read_table)
            return [r for r in rows if r["user_id"] == self._user_id]
        except Exception as e:
            msg = f"Failed to fetch rows from {self._read_table}: {e}"
            raise errors.AdapterError(msg) from e

    def _fetch_by_ids(self, ids: list["uuid.UUID"]) -> list[dict]:
        """Filter the user-scoped rows to the given IDs (order not guaranteed)."""
        id_strs = {str(i) for i in ids}
        return [r for r in self._fetch_rows() if r["id"] in id_strs]

    def _write(self, updates: entities.BackendUpdates, error_context: str) -> None:
        """Route a write through the cache, wrapping failures as AdapterError.

        Raises:
            AdapterError: If the underlying write fails.

        """
        try:
            self._cache.write(self._write_table, updates)
        except Exception as e:
            msg = f"{error_context}: {e}"
            raise errors.AdapterError(msg) from e

    # -- Repository[EntityT] (use-case facing) ------------------------------

    def get_all(self) -> list[EntityT]:
        """Return all records for the current user."""
        return [self._parse(row) for row in self._fetch_rows()]

    def get_by_ids(self, ids: list["uuid.UUID"]) -> list[EntityT]:
        """Return the records matching the given IDs."""
        return [self._parse(row) for row in self._fetch_by_ids(ids)]

    def save(self, item: EntityT) -> None:
        """Insert or update a single record (Supabase upsert on ``id``)."""
        self._write(
            entities.BackendUpdates(added_rows=[item.model_dump(mode="json")]),
            f"Failed to save row to {self._write_table}",
        )

    def apply(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of inserts, edits, and deletes; no-op batch is skipped."""
        if not (updates.added_rows or updates.edited_rows or updates.deleted_rows):
            return
        self._write(updates, f"Failed to apply updates to {self._write_table}")

    # -- GridDataSource (UI facing) -----------------------------------------

    def rows(self) -> list[pydantic.BaseModel]:
        """Return all display rows as typed ``view_model`` instances."""
        return [self._view_model.model_validate(row) for row in self._fetch_rows()]

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of unique non-null values for a column.

        Null values are dropped so they never surface as filter-widget options.
        """
        return {
            row[column_name]
            for row in self._fetch_rows()
            if row.get(column_name) is not None
        }


# ---------------------------------------------------------------------------
# Per-aggregate factories. Each owns its aggregate's parser, view model, and
# table names, and returns a repository typed on the aggregate's entity so use
# cases and composition stay statically typed.
# ---------------------------------------------------------------------------


def bank_account_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.BankAccountModel]:
    """Build the bank-accounts repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.BankAccountModel.model_validate,
        view_model=read_models.BankAccountView,
        read_table=table_names.ViewNames.BANK_ACCOUNTS,
        write_table=table_names.TableNames.BANK_ACCOUNTS,
        cache=cache,
    )


def budget_tracker_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.BudgetTrackerItemModel]:
    """Build the budget-tracker repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.BudgetTrackerItemModel.model_validate,
        view_model=read_models.BudgetTrackerView,
        read_table=table_names.ViewNames.BUDGET_TRACKER,
        write_table=table_names.TableNames.BUDGET_TRACKER,
        cache=cache,
    )


def expense_source_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.ExpenseSourceModel]:
    """Build the expense-sources repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.ExpenseSourceModel.model_validate,
        view_model=read_models.ExpenseSourceView,
        read_table=table_names.ViewNames.EXPENSE_SOURCES,
        write_table=table_names.TableNames.EXPENSE_SOURCES,
        cache=cache,
    )


def income_source_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.IncomeSourceModel]:
    """Build the income-sources repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.IncomeSourceModel.model_validate,
        view_model=read_models.IncomeSourceView,
        read_table=table_names.ViewNames.INCOME_SOURCES,
        write_table=table_names.TableNames.INCOME_SOURCES,
        cache=cache,
    )


def one_off_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.OneOffItemModel]:
    """Build the one-offs repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.OneOffItemModel.model_validate,
        view_model=read_models.OneOffView,
        read_table=table_names.ViewNames.ONE_OFFS,
        write_table=table_names.TableNames.ONE_OFFS,
        cache=cache,
    )


def subscription_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.SubscriptionModel]:
    """Build the subscriptions repository."""
    return SupabaseRepository(
        user_id,
        parse=entities.SubscriptionModel.model_validate,
        view_model=read_models.SubscriptionView,
        read_table=table_names.ViewNames.SUBSCRIPTIONS,
        write_table=table_names.TableNames.SUBSCRIPTIONS,
        cache=cache,
    )


def payment_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
) -> SupabaseRepository[entities.AnyPaymentModel]:
    """Build the payments repository.

    Payments have no SQL view — reads hit the raw table, and rows are parsed
    into ``ExpensePaymentModel`` / ``IncomePaymentModel`` via the discriminated
    union rather than a single entity's ``model_validate``.
    """
    return SupabaseRepository(
        user_id,
        parse=_parse_payment,
        view_model=read_models.PaymentView,
        read_table=table_names.TableNames.PAYMENTS,
        write_table=table_names.TableNames.PAYMENTS,
        cache=cache,
    )
