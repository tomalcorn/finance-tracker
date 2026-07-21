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

# StrEnum members, so they double as the DB string values in an eq filter.
_PERSONAL: str = entities.OwnershipType.PERSONAL
_JOINT: str = entities.OwnershipType.JOINT


def _parse_payment(row: entities.JsonDict) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


@dataclasses.dataclass(frozen=True)
class RepoSpec[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel]:
    """The per-aggregate configuration a ``SupabaseRepository`` needs."""

    parse: "Callable[[entities.JsonDict], EntityT]"
    view_model: type[ViewT]
    read_table: table_names.ViewNames | table_names.TableNames
    write_table: table_names.TableNames
    ownership_scoped: bool = False
    """Whether rows carry the ``personal``/``joint`` ownership dimension.

    When true, reads and cache invalidation split into a personal slice
    (``{user_id}:{table}``) plus one joint slice per account the user belongs to
    (``joint:{account_id}:{table}``). The two joint tables themselves have no
    ownership dimension and leave this false, keeping the single-key behaviour.
    """


class SupabaseRepository[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel](
    repository.Repository[EntityT],
):
    """Read and write one aggregate through the injected cache gateway.

    The cache is shared across sessions and keyed per slice. A user's personal
    rows live under ``{user_id}:{table}``; joint rows live under
    ``joint:{account_id}:{table}``, a key every member of the account shares, so
    one member's joint write busts the same entry the other member reads. RLS
    scopes each DB read, and the slice filters keep personal and joint rows in
    their own entries (see ``ownership_scoped`` on ``RepoSpec``).
    """

    def __init__(
        self,
        user_id: str,
        spec: "RepoSpec[EntityT, ViewT]",
        cache: "cache_mod.CacheGateway",
        connection: "st_supabase_connection.SupabaseConnection",
        joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
    ) -> None:
        """Bind the repository to a user, its spec, the cache, and a connection.

        Args:
            user_id: The current user's Auth0 id, scoping the personal slice key.
            spec: The per-aggregate configuration.
            cache: The injected cache gateway.
            connection: The Supabase connection.
            joint_account_ids: The joint accounts the user belongs to. Drives the
                joint read slices and the joint invalidation keys; empty for a
                personal-only user or a non-ownership-scoped aggregate.

        """
        self._user_id = user_id
        self._spec = spec
        self._cache = cache
        self._connection = connection
        self._joint_account_ids = joint_account_ids

    def _personal_key(
        self,
        table: "table_names.ViewNames | table_names.TableNames",
    ) -> str:
        """Return the user-scoped cache key for a table or view."""
        return f"{self._user_id}:{table}"

    def _joint_key(
        self,
        account_id: "uuid.UUID",
        table: "table_names.ViewNames | table_names.TableNames",
    ) -> str:
        """Return the account-scoped cache key shared by an account's members."""
        return f"joint:{account_id}:{table}"

    def _read_slices(self) -> "list[tuple[str, dict[str, str]]]":
        """Return the ``(cache_key, eq_filters)`` slices that form a full read.

        A non-ownership-scoped aggregate is a single unfiltered whole-table read
        under the user key. An ownership-scoped one is the user's personal slice
        plus one joint slice per account they belong to, each filtered so its
        cache entry holds only that slice's rows.
        """
        table = self._spec.read_table
        if not self._spec.ownership_scoped:
            return [(self._personal_key(table), {})]
        slices = [(self._personal_key(table), {"ownership_type": _PERSONAL})]
        slices.extend(
            (
                self._joint_key(account_id, table),
                {"ownership_type": _JOINT, "joint_account_id": str(account_id)},
            )
            for account_id in self._joint_account_ids
        )
        return slices

    def _loader_for(
        self,
        eq_filters: dict[str, str],
    ) -> "Callable[[], list[entities.JsonDict]]":
        """Return a cache-miss loader that fetches one slice's rows."""

        def _load() -> list[entities.JsonDict]:
            return client.fetch_table(
                str(self._spec.read_table),
                "*",
                self._connection,
                eq_filters or None,
            )

        return _load

    def _fetch_rows(self) -> list[entities.JsonDict]:
        rows: list[entities.JsonDict] = []
        try:
            for key, eq_filters in self._read_slices():
                rows.extend(
                    self._cache.get_from_or_load_cache(
                        key,
                        self._loader_for(eq_filters),
                    ),
                )
        except adapter_errors.AdapterError as e:
            msg = f"Failed to fetch rows from {self._spec.read_table}: {e}"
            raise errors.RepositoryError(msg) from e
        return rows

    def _fetch_by_ids(self, ids: list["uuid.UUID"]) -> list[entities.JsonDict]:
        id_strs = {str(i) for i in ids}
        return [row for row in self._fetch_rows() if row["id"] in id_strs]

    def _affected_keys(self) -> list[str]:
        """Return the cache keys a write to this aggregate busts.

        The written table plus every view that depends on it (Supabase schema
        knowledge that belongs on the driven side), each under the user's
        personal key and — for an ownership-scoped aggregate — under the joint
        key of every account the user belongs to. Busting a purely-personal
        write's joint keys too is a cheap over-invalidation that avoids
        inspecting each written row's ownership.
        """
        views = table_names.VIEWS_AFFECTED_BY.get(self._spec.write_table, [])
        tables = (self._spec.write_table, *views)
        keys = [self._personal_key(t) for t in tables]
        if self._spec.ownership_scoped:
            keys.extend(
                self._joint_key(account_id, t)
                for account_id in self._joint_account_ids
                for t in tables
            )
        return keys

    def get_all(self) -> list[EntityT]:
        """Return all records for the current user."""
        return [self._spec.parse(row) for row in self._fetch_rows()]

    def get_by_ids(self, ids: list["uuid.UUID"]) -> list[EntityT]:
        """Return the records matching the given IDs."""
        return [self._spec.parse(row) for row in self._fetch_by_ids(ids)]

    def save(self, item: EntityT) -> None:
        """Insert or update a single record.

        Translates the adapter's own ``AdapterError`` into the port-level
        ``RepositoryError`` at the port boundary; a genuine programming error is
        left to propagate untouched rather than being masked as a write failure.
        """
        try:
            client.upsert_row(
                str(self._spec.write_table),
                item.model_dump(mode="json"),
                self._connection,
            )
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"Failed to save row to {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def apply(self, updates: entities.BackendUpdates) -> None:
        """Apply a batch of inserts, edits, and deletes; a no-op batch is skipped.

        Translates the adapter's own ``AdapterError`` into the port-level
        ``RepositoryError`` at the port boundary; a genuine programming error is
        left to propagate untouched rather than being masked as a write failure.
        """
        if not (updates.added_rows or updates.edited_rows or updates.deleted_rows):
            return
        try:
            client.update_backend(
                str(self._spec.write_table),
                updates,
                self._connection,
            )
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"Failed to apply updates to {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def rows(self) -> list[ViewT]:
        """Return all display rows as typed view models."""
        return [self._spec.view_model.model_validate(row) for row in self._fetch_rows()]

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of unique non-null values for a column.

        List-valued columns (e.g. ``budget_tracker_ids``) are flattened into
        their individual elements so the result stays a set of hashable scalars
        rather than trying — and failing — to hash the list itself.
        """
        values: set[object] = set()
        for row in self._fetch_rows():
            value = row.get(column_name)
            if value is None:
                continue
            if isinstance(value, list):
                values.update(value)
            else:
                values.add(value)
        return values


def bank_account_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.BankAccountModel, read_models.BankAccountView]:
    """Build the bank-accounts repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.BankAccountModel.model_validate,
            view_model=read_models.BankAccountView,
            read_table=table_names.ViewNames.BANK_ACCOUNTS,
            write_table=table_names.TableNames.BANK_ACCOUNTS,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def budget_tracker_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.BudgetTrackerItemModel, read_models.BudgetTrackerView]:
    """Build the budget-tracker repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.BudgetTrackerItemModel.model_validate,
            view_model=read_models.BudgetTrackerView,
            read_table=table_names.ViewNames.BUDGET_TRACKER,
            write_table=table_names.TableNames.BUDGET_TRACKER,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def expense_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.ExpenseSourceModel, read_models.ExpenseSourceView]:
    """Build the expense-sources repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.ExpenseSourceModel.model_validate,
            view_model=read_models.ExpenseSourceView,
            read_table=table_names.ViewNames.EXPENSE_SOURCES,
            write_table=table_names.TableNames.EXPENSE_SOURCES,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def income_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.IncomeSourceModel, read_models.IncomeSourceView]:
    """Build the income-sources repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.IncomeSourceModel.model_validate,
            view_model=read_models.IncomeSourceView,
            read_table=table_names.ViewNames.INCOME_SOURCES,
            write_table=table_names.TableNames.INCOME_SOURCES,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def one_off_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.OneOffItemModel, read_models.OneOffView]:
    """Build the one-offs repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.OneOffItemModel.model_validate,
            view_model=read_models.OneOffView,
            read_table=table_names.ViewNames.ONE_OFFS,
            write_table=table_names.TableNames.ONE_OFFS,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def subscription_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
) -> SupabaseRepository[entities.SubscriptionModel, read_models.SubscriptionView]:
    """Build the subscriptions repository."""
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.SubscriptionModel.model_validate,
            view_model=read_models.SubscriptionView,
            read_table=table_names.ViewNames.SUBSCRIPTIONS,
            write_table=table_names.TableNames.SUBSCRIPTIONS,
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )


def joint_account_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[entities.JointAccountModel, read_models.JointAccountView]:
    """Build the joint-accounts repository.

    RLS scopes ``joint_accounts`` to the accounts the caller belongs to, so
    ``get_all`` answers "which joint accounts do I share" and ``save`` creates
    one. Like payments, joint accounts have no SQL view, so reads hit the raw
    table. The plain ``Repository`` surface (read + insert) covers what the joint
    use cases need, so no narrower named port is introduced here; a filtered read
    such as "members of this account" is added as an explicit method when a use
    case needs it, never as a generic filter argument.
    """
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.JointAccountModel.model_validate,
            view_model=read_models.JointAccountView,
            read_table=table_names.TableNames.JOINT_ACCOUNTS,
            write_table=table_names.TableNames.JOINT_ACCOUNTS,
        ),
        cache,
        connection,
    )


def joint_account_member_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
) -> SupabaseRepository[
    entities.JointAccountMemberModel,
    read_models.JointAccountMemberView,
]:
    """Build the joint-account membership repository.

    Membership is read + insert: ``get_all`` lists the caller's own membership
    rows (RLS on ``joint_account_members`` is own-rows-only) and ``save`` adds
    one. No SQL view, so reads hit the raw table. Inserting a *co-member's* row
    is blocked by that same RLS ``WITH CHECK`` on the app connection and belongs
    to the privileged create/invite flow (T6), not this plumbing.
    """
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.JointAccountMemberModel.model_validate,
            view_model=read_models.JointAccountMemberView,
            read_table=table_names.TableNames.JOINT_ACCOUNT_MEMBERS,
            write_table=table_names.TableNames.JOINT_ACCOUNT_MEMBERS,
        ),
        cache,
        connection,
    )


def payment_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    joint_account_ids: "frozenset[uuid.UUID]" = frozenset(),
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
            ownership_scoped=True,
        ),
        cache,
        connection,
        joint_account_ids,
    )
