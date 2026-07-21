"""Unit tests for the generic Supabase repository.

Reads go through an in-memory ``FakeCache`` standing in for the injected
``CacheGateway``; writes are asserted against a patched ``client``. Per-user
read isolation is the cache key's job now (``{user_id}:{table}`` plus row-level
security), so the repository no longer filters rows itself.
"""

import uuid
from collections.abc import Callable, Iterable
from unittest import mock

import pytest
import st_supabase_connection

from domain import entities, read_models
from driven_adapters import errors as adapter_errors
from driven_adapters.supabase import repository, table_names
from driving_adapters import cache as ui_cache
from ports import errors

_USER_ID = "auth0|test-user-123"
_CONN = mock.MagicMock(spec=st_supabase_connection.SupabaseConnection)


class FakeCache:
    """In-memory CacheGateway: serves fixed rows, records keys and invalidations."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        *,
        fetch_error: Exception | None = None,
    ) -> None:
        """Seed the fake with the rows a read should return, or an error to raise."""
        self._rows = rows if rows is not None else []
        self.requested_keys: list[str] = []
        self.invalidated: list[str] = []
        self._fetch_error = fetch_error

    def get_from_or_load_cache(
        self,
        key: str,
        loader: Callable[[], list[dict[str, object]]],  # noqa: ARG002 - loader unused; the fake serves fixed rows without hitting a backend
    ) -> list[dict[str, object]]:
        self.requested_keys.append(key)
        if self._fetch_error is not None:
            raise self._fetch_error
        return list(self._rows)

    def invalidate(self, keys: Iterable[str]) -> None:
        self.invalidated.extend(keys)


def _bank_view_row(  # noqa: PLR0913 - keyword-only test row builder; each field is an independent knob
    *,
    user_id: str = _USER_ID,
    row_id: uuid.UUID | None = None,
    name: str = "Current",
    starting_balance: float = 250.0,
    current_balance: float = 250.0,
    ownership_type: entities.OwnershipType = entities.OwnershipType.PERSONAL,
    joint_account_id: uuid.UUID | None = None,
) -> dict:
    """Return a bank_accounts_view-shaped row (carries the computed column)."""
    return read_models.BankAccountView(
        id=row_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        starting_balance=starting_balance,
        current_balance=current_balance,
        ownership_type=ownership_type,
        joint_account_id=joint_account_id,
    ).model_dump(mode="json")


class KeyedFakeCache:
    """CacheGateway fake serving different rows per cache key."""

    def __init__(self, rows_by_key: dict[str, list[dict]]) -> None:
        """Seed the fake with a ``key -> rows`` map."""
        self._rows_by_key = rows_by_key
        self.requested_keys: list[str] = []
        self.invalidated: list[str] = []

    def get_from_or_load_cache(
        self,
        key: str,
        loader: Callable[[], list[dict[str, object]]],  # noqa: ARG002 - fake serves fixed rows without a backend
    ) -> list[dict[str, object]]:
        self.requested_keys.append(key)
        return list(self._rows_by_key.get(key, []))

    def invalidate(self, keys: Iterable[str]) -> None:
        self.invalidated.extend(keys)


# ---------------------------------------------------------------------------
# Reads: parsing + user-scoped cache key
# ---------------------------------------------------------------------------


class TestGetAll:
    def test_parses_served_rows_into_entities(self) -> None:
        # Arrange
        rows = [_bank_view_row(name="Mine"), _bank_view_row(name="Also mine")]
        repo = repository.bank_account_repository(_USER_ID, FakeCache(rows), _CONN)

        # Act
        result = repo.get_all()

        # Assert
        assert all(isinstance(m, entities.BankAccountModel) for m in result)

    def test_reads_use_a_user_scoped_cache_key(self) -> None:
        # Arrange
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN)

        # Act
        repo.get_all()

        # Assert - key is {user_id}:{read view}, so users never share an entry
        assert cache.requested_keys == [
            f"{_USER_ID}:{table_names.ViewNames.BANK_ACCOUNTS}",
        ]

    def test_wraps_adapter_fetch_failure_in_repository_error(self) -> None:
        # Arrange - the client/loader surfaces backend failures as AdapterError
        boom = adapter_errors.SupabaseAdapterError("fetch boom")
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(fetch_error=boom),
            _CONN,
        )

        # Act
        with pytest.raises(errors.RepositoryError) as exc_info:
            repo.get_all()

        # Assert - names the read, and the original failure is the chained cause
        assert all(
            [
                "Failed to fetch rows" in str(exc_info.value),
                exc_info.value.__cause__ is boom,
            ],
        )

    def test_programming_error_on_fetch_is_not_translated(self) -> None:
        # Arrange - a genuine bug in the read path must not be masked as a
        # RepositoryError; it should propagate untouched so it stays diagnosable.
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(fetch_error=KeyError("id")),
            _CONN,
        )

        # Act / Assert
        with pytest.raises(KeyError):
            repo.get_all()


class TestGetByIds:
    def test_returns_only_matching_ids(self) -> None:
        # Arrange
        wanted = uuid.uuid4()
        rows = [
            _bank_view_row(row_id=wanted, name="Wanted"),
            _bank_view_row(name="Other"),
        ]
        repo = repository.bank_account_repository(_USER_ID, FakeCache(rows), _CONN)

        # Act
        result = repo.get_by_ids([wanted])

        # Assert
        assert [m.id for m in result] == [wanted]


# ---------------------------------------------------------------------------
# GridDataSource surface
# ---------------------------------------------------------------------------


class TestRows:
    def test_returns_view_models_with_computed_columns(self) -> None:
        # Arrange
        balance = 999.0
        row = _bank_view_row(current_balance=balance)
        repo = repository.bank_account_repository(_USER_ID, FakeCache([row]), _CONN)

        # Act
        result = repo.rows()

        # Assert
        assert result[0].current_balance == balance


class TestUniqueValues:
    def test_dedups_and_drops_nulls(self) -> None:
        # Arrange
        rows = [
            {"user_id": _USER_ID, "name": "A", "note": "x"},
            {"user_id": _USER_ID, "name": "A", "note": None},
            {"user_id": _USER_ID, "name": "B", "note": "y"},
        ]
        repo = repository.bank_account_repository(_USER_ID, FakeCache(rows), _CONN)

        # Act / Assert
        assert all(
            [
                repo.unique_values("name") == {"A", "B"},
                repo.unique_values("note") == {"x", "y"},
            ],
        )

    def test_flattens_list_valued_columns_into_their_elements(self) -> None:
        # Arrange - a list column (e.g. budget_tracker_ids) is unhashable as-is
        rows = [
            {"user_id": _USER_ID, "budget_tracker_ids": ["a", "b"]},
            {"user_id": _USER_ID, "budget_tracker_ids": ["b", "c"]},
        ]
        repo = repository.income_source_repository(_USER_ID, FakeCache(rows), _CONN)

        # Act
        result = repo.unique_values("budget_tracker_ids")

        # Assert
        assert result == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# Payments: discriminated-union parsing
# ---------------------------------------------------------------------------


class TestOwnershipScopedSlices:
    """Ownership-scoped reads split into a personal slice + per-account joint slices."""

    def test_reads_request_personal_then_joint_slice_keys(self) -> None:
        # Arrange - one joint account keeps the slice order deterministic
        account = uuid.uuid4()
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(
            _USER_ID,
            cache,
            _CONN,
            frozenset({account}),
        )

        # Act
        repo.get_all()

        # Assert - personal slice first, then the account's joint slice
        view = table_names.ViewNames.BANK_ACCOUNTS
        assert cache.requested_keys == [
            f"{_USER_ID}:{view}",
            f"joint:{account}:{view}",
        ]

    def test_a_personal_only_user_reads_just_the_user_key(self) -> None:
        # Arrange - no joint accounts, so no joint slices (today's behaviour)
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN)

        # Act
        repo.get_all()

        # Assert
        assert cache.requested_keys == [
            f"{_USER_ID}:{table_names.ViewNames.BANK_ACCOUNTS}",
        ]

    def test_get_all_merges_personal_and_joint_slice_rows(self) -> None:
        # Arrange - each slice key serves its own rows
        account = uuid.uuid4()
        view = table_names.ViewNames.BANK_ACCOUNTS
        cache = KeyedFakeCache(
            {
                f"{_USER_ID}:{view}": [_bank_view_row(name="Personal")],
                f"joint:{account}:{view}": [
                    _bank_view_row(
                        name="Joint",
                        ownership_type=entities.OwnershipType.JOINT,
                        joint_account_id=account,
                    ),
                ],
            },
        )
        repo = repository.bank_account_repository(
            _USER_ID,
            cache,
            _CONN,
            frozenset({account}),
        )

        # Act
        result = repo.get_all()

        # Assert
        assert {model.name for model in result} == {"Personal", "Joint"}

    def test_write_busts_the_accounts_joint_slice_key(self) -> None:
        # Arrange - a spec-less connection so the write chain (.table().insert())
        # is a no-op; the write path then reaches cache invalidation.
        account = uuid.uuid4()
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(
            _USER_ID,
            cache,
            mock.MagicMock(),
            frozenset({account}),
        )

        # Act - any write fans invalidation out to the user's joint keys
        repo.apply(entities.BackendUpdates(added_rows=[_bank_view_row()]))

        # Assert - the shared joint key is busted, so co-members refresh
        assert (
            f"joint:{account}:{table_names.TableNames.BANK_ACCOUNTS}"
            in cache.invalidated
        )


class TestCrossMemberStaleness:
    """The core fix: one member's joint write refreshes another member's read."""

    def test_a_partners_joint_write_reloads_the_shared_slice(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange - real cross-session cache; count joint-slice loads by filter
        ui_cache._get_data_cached.clear()
        ui_cache._key_versions.clear()
        account = uuid.uuid4()
        joint_filter = {
            "ownership_type": "joint",
            "joint_account_id": str(account),
        }
        loads: list[dict[str, str]] = []

        def _fake_fetch(
            table_name: str,  # noqa: ARG001 - signature mirrors client.fetch_table
            query_string: str,  # noqa: ARG001 - unused in the fake
            connection: object,  # noqa: ARG001 - unused in the fake
            eq_filters: dict[str, str] | None = None,
        ) -> list[dict[str, object]]:
            loads.append(eq_filters or {})
            return []

        monkeypatch.setattr(repository.client, "fetch_table", _fake_fetch)
        # A spec-less connection so A's write chain is a harmless no-op; reads are
        # served by the patched fetch_table, so the connection is otherwise unused.
        write_conn = mock.MagicMock()
        shared_cache = ui_cache.StreamlitCache()
        repo_a = repository.payment_repository(
            "auth0|a",
            shared_cache,
            write_conn,
            frozenset({account}),
        )
        repo_b = repository.payment_repository(
            "auth0|b",
            shared_cache,
            write_conn,
            frozenset({account}),
        )

        # Act - B warms its read, A writes a joint row, B reads again
        repo_b.get_all()
        joint_loads_before = loads.count(joint_filter)
        repo_a.apply(entities.BackendUpdates(added_rows=[{"id": str(uuid.uuid4())}]))
        repo_b.get_all()
        joint_loads_after = loads.count(joint_filter)

        # Assert - B's shared joint slice reloaded after A's write (was stale before)
        assert joint_loads_after == joint_loads_before + 1


class TestPaymentRepository:
    def test_get_all_parses_expense_and_income_into_correct_subtypes(self) -> None:
        # Arrange
        bank_account_id = uuid.uuid4()
        expense = entities.ExpensePaymentModel(
            user_id=_USER_ID,
            name="Groceries",
            expense=40.0,
            bank_account_id=bank_account_id,
        ).model_dump(mode="json")
        income = entities.IncomePaymentModel(
            user_id=_USER_ID,
            name="Salary",
            income=2000.0,
            bank_account_id=bank_account_id,
        ).model_dump(mode="json")
        repo = repository.payment_repository(
            _USER_ID,
            FakeCache([expense, income]),
            _CONN,
        )

        # Act
        result = repo.get_all()

        # Assert
        assert {type(p) for p in result} == {
            entities.ExpensePaymentModel,
            entities.IncomePaymentModel,
        }
