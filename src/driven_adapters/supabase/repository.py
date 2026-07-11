"""Supabase-backed implementation of the repository port.

One generic ``SupabaseRepository`` serves every aggregate; a ``RepoSpec``
carries the per-aggregate parser, view model, and table names. The factory
functions at the bottom build one typed repository per aggregate. The class
also satisfies the UI's ``GridDataSource`` port, so composition can pass a
repository straight to a grid.
"""

import dataclasses
from typing import TYPE_CHECKING

import pydantic

from domain import entities, read_models
from driven_adapters import errors as adapter_errors
from driven_adapters.supabase import client, table_names
from ports import errors, repository

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable

    import st_supabase_connection

    from driven_adapters import cache as cache_mod

_PaymentAdapter = pydantic.TypeAdapter(entities.AnyPaymentModel)


def _parse_payment(row: entities.JsonDict) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


@dataclasses.dataclass(frozen=True)
class RepoSpec[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel]:
    """The per-aggregate configuration a ``SupabaseRepository`` needs."""

    parse: "Callable[[entities.JsonDict], EntityT]"
    view_model: type[ViewT]
    read_table: table_names.ViewNames | table_names.TableNames
    write_table: table_names.TableNames


class SupabaseRepository[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel](
    repository.Repository[EntityT],
):
    """Read and write one aggregate through the injected cache gateway.

    The cache is shared across sessions, so reads are keyed per user
    (``{user_id}:{table}``); with row-level security scoping the DB read, each
    user's cache entry holds only their own rows.
    """

    def __init__(
        self,
        user_id: str,
        spec: "RepoSpec[EntityT, ViewT]",
        cache: "cache_mod.CacheGateway",
        connection: "st_supabase_connection.SupabaseConnection",
    ) -> None:
        """Bind the repository to a user, its spec, the cache, and a connection."""
        self._user_id = user_id
        self._spec = spec
        self._cache = cache
        self._connection = connection

    def _cache_key(
        self,
        table: "table_names.ViewNames | table_names.TableNames",
    ) -> str:
        """Return the user-scoped cache key for a table or view."""
        return f"{self._user_id}:{table}"

    def _load_rows(self) -> list[entities.JsonDict]:
        """Fetch every row of the read table from Supabase (a cache-miss loader)."""
        return client.fetch_table(str(self._spec.read_table), "*", self._connection)

    def _fetch_rows(self) -> list[entities.JsonDict]:
        try:
            return self._cache.get_from_or_load_cache(
                self._cache_key(self._spec.read_table),
                self._load_rows,
            )
        except adapter_errors.AdapterError as e:
            msg = f"Failed to fetch rows from {self._spec.read_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def _fetch_by_ids(self, ids: list["uuid.UUID"]) -> list[entities.JsonDict]:
        id_strs = {str(i) for i in ids}
        return [row for row in self._fetch_rows() if row["id"] in id_strs]

    def _affected_keys(self) -> list[str]:
        """Return the user-scoped cache keys a write to this aggregate busts.

        The written table plus every view that depends on it — Supabase schema
        knowledge that belongs on the driven side.
        """
        views = table_names.VIEWS_AFFECTED_BY.get(self._spec.write_table, [])
        return [self._cache_key(t) for t in (self._spec.write_table, *views)]

    def _write(self, updates: entities.BackendUpdates, error_context: str) -> None:
        """Persist a write via the client, then invalidate affected cached reads.

        Translates the adapter's own ``AdapterError`` into a domain-level
        ``RepositoryError`` at the port boundary. A genuine programming error is
        left to propagate untouched rather than being masked as a write failure.
        """
        try:
            client.update_backend(
                str(self._spec.write_table),
                updates,
                self._connection,
            )
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"{error_context}: {e}"
            raise errors.RepositoryError(msg) from e

    def get_all(self) -> list[EntityT]:
        """Return all records for the current user."""
        return [self._spec.parse(row) for row in self._fetch_rows()]

    def get_by_ids(self, ids: list["uuid.UUID"]) -> list[EntityT]:
        """Return the records matching the given IDs."""
        return [self._spec.parse(row) for row in self._fetch_by_ids(ids)]

    def save(self, item: EntityT) -> None:
        """Insert or update a single record."""
        self._write(
            entities.BackendUpdates(added_rows=[item.model_dump(mode="json")]),
            f"Failed to save row to {self._spec.write_table}",
        )

    def apply(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of inserts, edits, and deletes; a no-op batch is skipped."""
        if not (updates.added_rows or updates.edited_rows or updates.deleted_rows):
            return
        self._write(updates, f"Failed to apply updates to {self._spec.write_table}")

    def rows(self) -> list[ViewT]:
        """Return all display rows as typed view models."""
        return [self._spec.view_model.model_validate(row) for row in self._fetch_rows()]

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of unique non-null values for a column."""
        return {
            row[column_name]
            for row in self._fetch_rows()
            if row.get(column_name) is not None
        }


def bank_account_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.BankAccountModel, read_models.BankAccountView]:
    """Build the bank-accounts repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.BankAccountModel.model_validate,
            view_model=read_models.BankAccountView,
            read_table=table_names.ViewNames.BANK_ACCOUNTS,
            write_table=table_names.TableNames.BANK_ACCOUNTS,
        ),
        cache,
        connection,
    )


def budget_tracker_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.BudgetTrackerItemModel, read_models.BudgetTrackerView]:
    """Build the budget-tracker repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.BudgetTrackerItemModel.model_validate,
            view_model=read_models.BudgetTrackerView,
            read_table=table_names.ViewNames.BUDGET_TRACKER,
            write_table=table_names.TableNames.BUDGET_TRACKER,
        ),
        cache,
        connection,
    )


def expense_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.ExpenseSourceModel, read_models.ExpenseSourceView]:
    """Build the expense-sources repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.ExpenseSourceModel.model_validate,
            view_model=read_models.ExpenseSourceView,
            read_table=table_names.ViewNames.EXPENSE_SOURCES,
            write_table=table_names.TableNames.EXPENSE_SOURCES,
        ),
        cache,
        connection,
    )


def income_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.IncomeSourceModel, read_models.IncomeSourceView]:
    """Build the income-sources repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.IncomeSourceModel.model_validate,
            view_model=read_models.IncomeSourceView,
            read_table=table_names.ViewNames.INCOME_SOURCES,
            write_table=table_names.TableNames.INCOME_SOURCES,
        ),
        cache,
        connection,
    )


def one_off_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.OneOffItemModel, read_models.OneOffView]:
    """Build the one-offs repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.OneOffItemModel.model_validate,
            view_model=read_models.OneOffView,
            read_table=table_names.ViewNames.ONE_OFFS,
            write_table=table_names.TableNames.ONE_OFFS,
        ),
        cache,
        connection,
    )


def subscription_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.SubscriptionModel, read_models.SubscriptionView]:
    """Build the subscriptions repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.SubscriptionModel.model_validate,
            view_model=read_models.SubscriptionView,
            read_table=table_names.ViewNames.SUBSCRIPTIONS,
            write_table=table_names.TableNames.SUBSCRIPTIONS,
        ),
        cache,
        connection,
    )


def payment_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.AnyPaymentModel, read_models.PaymentView]:
    """Build the payments repository.

    Payments have no SQL view, so reads hit the raw table and rows are parsed
    into ``ExpensePaymentModel`` / ``IncomePaymentModel`` via the discriminated
    union rather than a single entity's ``model_validate``.
    """
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=_parse_payment,
            view_model=read_models.PaymentView,
            read_table=table_names.TableNames.PAYMENTS,
            write_table=table_names.TableNames.PAYMENTS,
        ),
        cache,
        connection,
    )
