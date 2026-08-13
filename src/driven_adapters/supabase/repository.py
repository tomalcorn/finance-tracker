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
from domain import errors as domain_errors
from driven_adapters import errors as adapter_errors
from driven_adapters.supabase import client, table_names
from ports import errors, repository

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import st_supabase_connection

    from driven_adapters import cache as cache_mod

_PaymentAdapter = pydantic.TypeAdapter(entities.AnyPaymentModel)


def _parse_payment(row: entities.RawRow) -> entities.AnyPaymentModel:
    return _PaymentAdapter.validate_python(row)


@dataclasses.dataclass(frozen=True)
class RepoSpec[EntityT: pydantic.BaseModel, ViewT: pydantic.BaseModel]:
    """The per-aggregate configuration a ``SupabaseRepository`` needs."""

    parse: "Callable[[entities.RawRow], EntityT]"
    view_model: type[ViewT]
    read_table: table_names.ViewNames | table_names.TableNames
    write_table: table_names.TableNames


@dataclasses.dataclass(frozen=True)
class OwnershipContext:
    """The owner and ownership fields for every row this repository writes.

    ``ownership_type`` is ``None`` for the aggregates with no ownership dimension
    (the two joint tables), whose rows carry only a ``user_id``.
    """

    user_id: str
    ownership_type: entities.OwnershipType | None
    joint_account_id: uuid.UUID | None

    def as_fields(self) -> entities.JsonDict:
        """Return the context as row fields, ready to complete a raw row."""
        fields: entities.JsonDict = {"user_id": self.user_id}
        if self.ownership_type is None:
            return fields
        fields["ownership_type"] = self.ownership_type.value
        fields["joint_account_id"] = (
            str(self.joint_account_id) if self.joint_account_id is not None else None
        )
        return fields

    def ownership_matches(self, entity: entities.HasOwnershipDimension) -> bool:
        """Return whether ``entity`` is owned the way this context writes."""
        return (
            entity.ownership_type is self.ownership_type
            and entity.joint_account_id == self.joint_account_id
        )


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
        return self._joint_cache_key(account_id, table)

    @staticmethod
    def _joint_cache_key(
        account_id: uuid.UUID,
        table: "table_names.ViewNames | table_names.TableNames",
    ) -> str:
        """Return the account-scoped key every member of an account computes."""
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

    def _ownership_context(self) -> OwnershipContext:
        """Return the owner/ownership fields this repository writes under.

        Raises:
            NoJointAccountError: The repository is joint but the user belongs to
                no joint account, so there is no account to write against.

        """
        account_id: uuid.UUID | None = None
        if self._ownership is entities.OwnershipType.JOINT:
            account_id = self._joint_account_id()
            if account_id is None:
                raise errors.NoJointAccountError(self._user_id)
        return OwnershipContext(self._user_id, self._ownership, account_id)

    def _affected_keys(self) -> list[str]:
        """Return the cache keys a write to this aggregate busts.

        The written table plus everything that depends on it — the views
        computed from it, and any table an ``ON DELETE CASCADE`` writes on its
        behalf (Supabase schema knowledge that belongs on the driven side) —
        each under this repository's own key. A repository only ever writes rows
        of its own ownership, so it only ever has to bust its own entries — and
        because a joint key is derived from the account, busting it reaches every
        member of it.
        """
        affected = table_names.CACHE_KEYS_AFFECTED_BY.get(self._spec.write_table, [])
        own = [self._cache_key(t) for t in (self._spec.write_table, *affected)]
        return own + self._cascaded_joint_keys()

    def _cascaded_joint_keys(self) -> list[str]:
        """Return the joint keys a cascade from this write reaches, if any.

        The one exception to "a repository busts only its own half". A cascade
        is the database writing rows on this repository's behalf, and
        ``CASCADES_ACROSS_OWNERSHIP`` names the cascades that land on the other
        side of the ownership split — so the rows really are moved, and the key
        holding them really must be busted, by the only repository that knows
        the write happened.

        Empty unless this is a personal repository whose table has such a
        cascade and the user has a joint account. The account id comes from the
        same memoised, cache-backed read every joint key already uses, so this
        costs no extra fetch.
        """
        if self._ownership is not entities.OwnershipType.PERSONAL:
            return []
        crossing = table_names.CASCADES_ACROSS_OWNERSHIP.get(
            self._spec.write_table,
            [],
        )
        if not crossing:
            return []
        account_id = self._joint_account_id()
        if account_id is None:
            return []
        return [self._joint_cache_key(account_id, t) for t in crossing]

    def _validated[ParsedT](
        self,
        rows: "Sequence[entities.RawRow]",
        parse: "Callable[[entities.RawRow], ParsedT]",
    ) -> list[ParsedT]:
        """Validate fetched rows, translating a malformed one at the boundary.

        The read counterpart of ``build_entities``' gate. A stored row that no
        longer satisfies its model is a persistence failure like any other, so
        it leaves as a ``RepositoryError`` rather than as the raw pydantic
        ``ValidationError``, which would cross the port untranslated and reach
        the user as a traceback instead of the page's error boundary.

        Args:
            rows: The raw rows just fetched.
            parse: Validates one raw row into its model.

        Returns:
            The validated rows.

        Raises:
            RepositoryError: Any row failed to validate.

        """
        try:
            return [parse(row) for row in rows]
        except (pydantic.ValidationError, domain_errors.DomainError) as e:
            # A model validator raising a DomainError is not wrapped by pydantic
            # (DomainError is not a ValueError), so catch it too — as the write
            # gate does.
            msg = f"Malformed row read from {self._spec.read_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def get_all(self) -> list[EntityT]:
        """Return all records for the current user."""
        return self._validated(self._fetch_rows(), self._spec.parse)

    def get_by_ids(self, ids: list["uuid.UUID"]) -> list[EntityT]:
        """Return the records matching the given IDs."""
        return self._validated(self._fetch_by_ids(ids), self._spec.parse)

    def build_entities(self, rows: "Sequence[entities.RawRow]") -> list[EntityT]:
        """Complete raw rows with this repository's write context, then validate.

        The write gate: a row arrives missing the fields that decide whose it is,
        and leaves as a complete entity. The context is applied to the raw fields
        *before* validation, so the entity is valid the moment it exists and is
        never patched afterwards.
        """
        context = self._ownership_context().as_fields()
        try:
            return [self._spec.parse({**row, **context}) for row in rows]
        except (pydantic.ValidationError, domain_errors.DomainError) as e:
            # A model validator raising a DomainError is not wrapped by pydantic
            # (DomainError is not a ValueError), so catch it too: both are the
            # same failure — this row is not valid for this aggregate.
            msg = f"Invalid row for {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def save_entities(self, items: "Sequence[EntityT]") -> None:
        """Upsert complete entities, busting this repository's cache keys once.

        Translates the adapter's own ``AdapterError`` into the port-level
        ``RepositoryError`` at the port boundary; a genuine programming error is
        left to propagate untouched rather than being masked as a write failure.
        """
        if not items:
            return
        self._assert_owned(items)
        try:
            client.upsert_rows(
                str(self._spec.write_table),
                [item.model_dump(mode="json") for item in items],
                self._connection,
            )
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"Failed to save rows to {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def _assert_owned(self, items: "Sequence[EntityT]") -> None:
        """Reject entities not owned the way this repository writes.

        A repository serves one ownership mode, so persisting a personal entity
        through a joint repository (or the reverse) would misfile the row and bust
        the wrong cache keys. Fail loudly at the boundary instead.

        Raises:
            RepositoryError: Any entity's ownership does not match this mode.

        """
        owned = [
            item for item in items if isinstance(item, entities.HasOwnershipDimension)
        ]
        if not owned:
            # The joint tables' entities carry no ownership dimension, so there
            # is nothing to match against.
            return
        context = self._ownership_context()
        if all(context.ownership_matches(item) for item in owned):
            return
        msg = (
            f"Cannot save rows to {self._spec.write_table}: an entity's ownership "
            f"does not match this repository's {self._ownership} mode."
        )
        raise errors.RepositoryError(msg)

    def apply_edits(self, edits: entities.EditedRows) -> None:
        """Patch the given columns of stored rows; an empty patch set is skipped.

        Edits act on rows already of this repository's ownership (the read that
        surfaced them was mode-filtered) and cannot change identity or ownership
        columns, so they do not pass through the entity gate.
        """
        if not edits:
            return
        try:
            client.update_rows(str(self._spec.write_table), edits, self._connection)
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"Failed to apply edits to {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def apply_deletions(self, ids: entities.DeletedIds) -> None:
        """Delete the rows with the given ids; an empty list is skipped."""
        if not ids:
            return
        try:
            client.delete_rows(str(self._spec.write_table), ids, self._connection)
            self._cache.invalidate(self._affected_keys())
        except adapter_errors.AdapterError as e:
            msg = f"Failed to delete rows from {self._spec.write_table}: {e}"
            raise errors.RepositoryError(msg) from e

    def rows(self) -> list[ViewT]:
        """Return all display rows as typed view models."""
        return self._validated(self._fetch_rows(), self._spec.view_model.model_validate)

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


def quick_button_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
) -> SupabaseRepository[entities.QuickButtonModel, read_models.QuickButtonView]:
    """Build the quick-buttons repository.

    Quick buttons have no SQL view, so reads hit the raw table.
    """
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.QuickButtonModel.model_validate,
            view_model=read_models.QuickButtonView,
            read_table=table_names.TableNames.QUICK_BUTTONS,
            write_table=table_names.TableNames.QUICK_BUTTONS,
        ),
        cache,
        connection,
        ownership,
    )


def user_settings_repository(
    user_id: str,
    cache: "cache_mod.CacheGateway",
    connection: "st_supabase_connection.SupabaseConnection",
    ownership: entities.OwnershipType,
) -> SupabaseRepository[entities.UserSettingsModel, read_models.UserSettingsView]:
    """Build the user-settings repository.

    Settings have no SQL view, so reads hit the raw table. Ownership-scoped like
    every other owned aggregate, which is exactly what keeps the personal and
    joint preferences apart: a ``JOINT`` repository reads and writes the one row
    belonging to the account, under the account-derived cache key both members
    resolve, so either member's change reaches the other.
    """
    return SupabaseRepository(
        user_id,
        RepoSpec(
            parse=entities.UserSettingsModel.model_validate,
            view_model=read_models.UserSettingsView,
            read_table=table_names.TableNames.USER_SETTINGS,
            write_table=table_names.TableNames.USER_SETTINGS,
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
