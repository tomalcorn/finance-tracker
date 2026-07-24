"""Supabase-backed implementation of the repository port.

One generic ``SupabaseRepository`` serves every aggregate; a ``RepoSpec``
carries the per-aggregate parser, view model, and table names. The factory
functions at the bottom build one typed repository per aggregate. The class
also satisfies the UI's ``GridDataSource`` port, so composition can pass a
repository straight to a grid.
"""

import dataclasses
import functools
import uuid
from typing import TYPE_CHECKING

import pydantic

from domain import entities, read_models
from driven_adapters import errors as adapter_errors
from driven_adapters.supabase import client, table_names
from ports import errors, repository

if TYPE_CHECKING:
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
    """Read and write one aggregate, in one ownership mode, through the cache.

    ``ownership`` selects what the repository sees and where it caches:

    * ``PERSONAL`` — the user's personal rows, keyed ``{user_id}:{table}``.
    * ``JOINT`` — the joint rows of the user's joint account, keyed
      ``joint:{account_id}:{table}``. That key is derived from the account, not
      the user, so **every member computes the same key**: one member's joint
      write busts exactly the entry the other member reads.
    * ``None`` — no ownership dimension (the two joint tables), keyed
      ``{user_id}:{table}`` with no filter.

    RLS already restricts every read to rows the user may see, so the mode
    filter only narrows that to the half being displayed; the account id is
    needed for the cache key, not for the query.
    """

    def __init__(
        self,
        user_id: str,
        spec: "RepoSpec[EntityT, ViewT]",
        cache: "cache_mod.CacheGateway",
        connection: "st_supabase_connection.SupabaseConnection",
        ownership: entities.OwnershipType | None,
    ) -> None:
        """Bind the repository to a user, spec, cache, connection and mode.

        ``ownership`` is required rather than defaulted: an aggregate that has
        the ownership dimension must say which half it serves, and passing
        ``None`` (no dimension at all, the two joint tables) is a decision worth
        making explicitly at the call site.
        """
        self._user_id = user_id
        self._spec = spec
        self._cache = cache
        self._connection = connection
        self._ownership = ownership
        self._account_id: uuid.UUID | None = None
        self._account_loaded = False

    def _joint_account_id(self) -> "uuid.UUID | None":
        """Return the user's joint account id, or None if they have none.

        A user belongs to at most one joint account, so this is a single id. It
        is read through the cache under ``{user_id}:joint_accounts`` — the entry
        the joint-accounts repo also fills, so it costs one fetch per session —
        and memoised so a repository's read and write paths agree.
        """
        if not self._account_loaded:
            accounts = table_names.TableNames.JOINT_ACCOUNTS
            rows = self._cache.get_from_or_load_cache(
                f"{self._user_id}:{accounts}",
                functools.partial(
                    client.fetch_table,
                    str(accounts),
                    "*",
                    self._connection,
                ),
            )
            self._account_id = uuid.UUID(str(rows[0]["id"])) if rows else None
            self._account_loaded = True
        return self._account_id

    def _cache_key(
        self,
        table: "table_names.ViewNames | table_names.TableNames",
    ) -> str:
        """Return this mode's cache key for a table or view.

        Raises:
            NoJointAccountError: The repository is joint but the user belongs to
                no joint account, so there is no account to key against — a
                caller asking a joint repository for data it cannot have.

        """
        if self._ownership is not entities.OwnershipType.JOINT:
            return f"{self._user_id}:{table}"
        account_id = self._joint_account_id()
        if account_id is None:
            raise errors.NoJointAccountError(self._user_id)
        return f"joint:{account_id}:{table}"

    def _eq_filters(self) -> dict[str, str]:
        """Return the equality filter selecting this mode's rows."""
        if self._ownership is None:
            return {}
        filters: dict[str, str] = {"ownership_type": self._ownership}
        return filters

    def _load_rows(self, eq_filters: dict[str, str]) -> list[entities.JsonDict]:
        """Fetch this mode's rows from Supabase (a cache-miss loader)."""
        return client.fetch_table(
            str(self._spec.read_table),
            "*",
            self._connection,
            eq_filters or None,
        )

    def _fetch_rows(self) -> list[entities.JsonDict]:
        try:
            return self._cache.get_from_or_load_cache(
                self._cache_key(self._spec.read_table),
                functools.partial(self._load_rows, self._eq_filters()),
            )
        except adapter_errors.AdapterError as e:
            msg = f"Failed to fetch rows from {self._spec.read_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def _fetch_by_ids(self, ids: list["uuid.UUID"]) -> list[entities.JsonDict]:
        id_strs = {str(i) for i in ids}
        return [row for row in self._fetch_rows() if row["id"] in id_strs]

    def _stamp_ownership(self, row: entities.JsonDict) -> entities.JsonDict:
        """Stamp this repository's ownership onto a row about to be inserted.

        A repository writes only rows of its own ownership, so every insert it
        makes must carry its mode's ``ownership_type`` (and, for joint, the
        account id) regardless of what the caller supplied — the grid add-row
        dialog builds a bare row that otherwise defaults to personal. The two
        joint tables have no ownership dimension (ownership ``None``), so their
        rows pass through untouched.

        Raises:
            NoJointAccountError: The repository is joint but the user belongs to
                no joint account, so there is no account to stamp.

        """
        if self._ownership is None:
            return row
        stamped: entities.JsonDict = {**row, "ownership_type": self._ownership.value}
        if self._ownership is entities.OwnershipType.JOINT:
            account_id = self._joint_account_id()
            if account_id is None:
                raise errors.NoJointAccountError(self._user_id)
            stamped["joint_account_id"] = str(account_id)
        else:
            stamped["joint_account_id"] = None
        return stamped

    def _affected_keys(self) -> list[str]:
        """Return the cache keys a write to this aggregate busts.

        The written table plus every view that depends on it (Supabase schema
        knowledge that belongs on the driven side), each under this repository's
        own key. A repository only ever writes rows of its own ownership, so it
        only ever has to bust its own entries — and because a joint key is
        derived from the account, busting it reaches every member of it.
        """
        views = table_names.VIEWS_AFFECTED_BY.get(self._spec.write_table, [])
        return [self._cache_key(t) for t in (self._spec.write_table, *views)]

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
                self._stamp_ownership(item.model_dump(mode="json")),
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
            # Inserts establish a row's ownership, so stamp this mode's ownership
            # onto every added row; edits/deletes act on rows already of this
            # ownership (the read that surfaced them was mode-filtered), so their
            # ownership columns are left untouched.
            stamped = updates.model_copy(
                update={
                    "added_rows": [
                        self._stamp_ownership(row) for row in updates.added_rows
                    ],
                },
            )
            client.update_backend(
                str(self._spec.write_table),
                stamped,
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
    ownership: entities.OwnershipType,
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
        ownership,
    )


def budget_tracker_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
    )


def expense_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
    )


def income_source_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
    )


def one_off_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
    )


def subscription_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
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
        None,  # no ownership dimension on the joint tables
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
        None,  # no ownership dimension on the joint tables
    )


def payment_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
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
        ownership,
    )
