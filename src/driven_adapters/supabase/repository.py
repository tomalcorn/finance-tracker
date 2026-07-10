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
from driven_adapters import cache as cache_mod
from driven_adapters import errors
from driven_adapters.supabase import table_names
from ports import repository

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable

_PaymentAdapter = pydantic.TypeAdapter(entities.AnyPaymentModel)


def _parse_payment(row: dict[str, object]) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


@dataclasses.dataclass(frozen=True)
class RepoSpec[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel]:
    """The per-aggregate configuration a ``SupabaseRepository`` needs."""

    parse: "Callable[[dict[str, object]], EntityT]"
    view_model: type[ViewT]
    read_table: table_names.ViewNames | table_names.TableNames
    write_table: table_names.TableNames


class SupabaseRepository[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel](
    repository.Repository[EntityT],
):
    """Read and write one aggregate through the injected cache gateway.

    Reads are re-scoped to ``user_id`` in Python because the cache is shared
    across sessions and keyed by table only.
    """

    def __init__(
        self,
        user_id: str,
        spec: "RepoSpec[EntityT, ViewT]",
        cache: cache_mod.CacheGateway,
    ) -> None:
        """Bind the repository to a user, its aggregate spec, and the cache."""
        self._user_id = user_id
        self._spec = spec
        self._cache = cache

    def _fetch_rows(self) -> list[dict[str, object]]:
        try:
            rows = self._cache.fetch(self._spec.read_table)
        except Exception as e:
            msg = f"Failed to fetch rows from {self._spec.read_table}: {e}"
            raise errors.AdapterError(msg) from e
        return [row for row in rows if row["user_id"] == self._user_id]

    def _fetch_by_ids(self, ids: list["uuid.UUID"]) -> list[dict[str, object]]:
        id_strs = {str(i) for i in ids}
        return [row for row in self._fetch_rows() if row["id"] in id_strs]

    def _write(self, updates: entities.BackendUpdates, error_context: str) -> None:
        """Send a write to the cache, translating any failure into AdapterError.

        Keeps Supabase/cache exceptions from leaking past the adapter boundary:
        callers only ever see a domain-level ``AdapterError``.
        """
        try:
            self._cache.write(self._spec.write_table, updates)
        except Exception as e:
            msg = f"{error_context}: {e}"
            raise errors.AdapterError(msg) from e

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
    cache: cache_mod.CacheGateway,
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
    )


def budget_tracker_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )


def expense_source_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )


def income_source_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )


def one_off_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )


def subscription_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )


def payment_repository(
    user_id: str,
    cache: cache_mod.CacheGateway,
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
    )
