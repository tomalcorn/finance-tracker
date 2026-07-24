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
_PERSONAL = entities.OwnershipType.PERSONAL
_JOINT = entities.OwnershipType.JOINT
_CONN = mock.MagicMock(spec=st_supabase_connection.SupabaseConnection)

# The key an ownership-scoped repo reads to discover the user's joint accounts.
# The fakes serve it but keep it out of ``requested_keys`` so the slice-key
# assertions stay focused on the aggregate read under test.
_JOINT_ACCOUNTS_KEY = f"{_USER_ID}:{table_names.TableNames.JOINT_ACCOUNTS}"


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
        if self._fetch_error is not None:
            raise self._fetch_error
        if key == _JOINT_ACCOUNTS_KEY:
            return []  # personal-only: no joint accounts discovered
        self.requested_keys.append(key)
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
        if key != _JOINT_ACCOUNTS_KEY:
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
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(rows),
            _CONN,
            _PERSONAL,
        )

        # Act
        result = repo.get_all()

        # Assert
        assert all(isinstance(m, entities.BankAccountModel) for m in result)

    def test_reads_use_a_user_scoped_cache_key(self) -> None:
        # Arrange
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN, _PERSONAL)

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
            _PERSONAL,
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
            _PERSONAL,
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
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(rows),
            _CONN,
            _PERSONAL,
        )

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
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache([row]),
            _CONN,
            _PERSONAL,
        )

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
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(rows),
            _CONN,
            _PERSONAL,
        )

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
        repo = repository.income_source_repository(
            _USER_ID,
            FakeCache(rows),
            _CONN,
            _PERSONAL,
        )

        # Act
        result = repo.unique_values("budget_tracker_ids")

        # Assert
        assert result == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# Payments: discriminated-union parsing
# ---------------------------------------------------------------------------


class TestOwnershipModes:
    """A repository reads and writes one ownership mode: personal or joint."""

    def test_personal_reads_use_the_user_key(self) -> None:
        # Arrange
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN, _PERSONAL)

        # Act
        repo.get_all()

        # Assert
        assert cache.requested_keys == [
            f"{_USER_ID}:{table_names.ViewNames.BANK_ACCOUNTS}",
        ]

    def test_personal_reads_filter_to_personal_rows(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(),
            _CONN,
            _PERSONAL,
        )

        # Act
        filters = repo._eq_filters()

        # Assert
        assert filters == {"ownership_type": _PERSONAL}

    def test_joint_reads_use_the_account_key_not_the_user_key(self) -> None:
        # Arrange - the account is discovered through the joint_accounts key
        account = uuid.uuid4()
        cache = KeyedFakeCache({_JOINT_ACCOUNTS_KEY: [{"id": str(account)}]})
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN, _JOINT)

        # Act
        repo.get_all()

        # Assert - keyed by account, so both members land on the same entry
        assert cache.requested_keys == [
            f"joint:{account}:{table_names.ViewNames.BANK_ACCOUNTS}",
        ]

    def test_joint_reads_filter_to_joint_rows(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(
            _USER_ID,
            KeyedFakeCache({}),
            _CONN,
            _JOINT,
        )

        # Act
        filters = repo._eq_filters()

        # Assert - RLS already limits to the user's account, so mode is enough
        assert filters == {"ownership_type": _JOINT}

    def test_joint_repo_raises_when_the_user_has_no_account(self) -> None:
        # Arrange - no joint account rows for this user
        cache = KeyedFakeCache({})
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN, _JOINT)

        # Act / Assert - asking a joint repo for data the user cannot have is a
        # caller error, not an empty result
        with pytest.raises(errors.NoJointAccountError) as exc_info:
            repo.get_all()
        assert exc_info.value.user_id == _USER_ID

    def test_joint_write_busts_the_shared_account_key(self) -> None:
        # Arrange - a spec-less connection so the write chain (.table().insert())
        # is a no-op; the write path then reaches cache invalidation.
        account = uuid.uuid4()
        cache = KeyedFakeCache({_JOINT_ACCOUNTS_KEY: [{"id": str(account)}]})
        repo = repository.bank_account_repository(
            _USER_ID,
            cache,
            mock.MagicMock(),
            _JOINT,
        )

        # Act
        repo.apply(entities.BackendUpdates(added_rows=[_bank_view_row()]))

        # Assert - the shared joint key is busted, so co-members refresh
        assert (
            f"joint:{account}:{table_names.TableNames.BANK_ACCOUNTS}"
            in cache.invalidated
        )

    def test_personal_write_leaves_joint_keys_alone(self) -> None:
        # Arrange
        cache = FakeCache([_bank_view_row()])
        repo = repository.bank_account_repository(
            _USER_ID,
            cache,
            mock.MagicMock(),
            _PERSONAL,
        )

        # Act
        repo.apply(entities.BackendUpdates(added_rows=[_bank_view_row()]))

        # Assert - a personal write only ever touches user-scoped keys
        assert not any(key.startswith("joint:") for key in cache.invalidated)


class TestCrossMemberStaleness:
    """The core fix: one member's joint write refreshes another member's read."""

    def test_a_partners_joint_write_reloads_the_shared_slice(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange - real cross-session cache; count joint reads by filter. RLS
        # already limits each member to their own account, so the mode is the
        # whole filter; the account only shows up in the cache key.
        ui_cache._get_data_cached.clear()
        ui_cache._key_versions.clear()
        account = uuid.uuid4()
        joint_filter: dict[str, str] = {"ownership_type": _JOINT}
        loads: list[dict[str, str]] = []

        def _fake_fetch(
            table_name: str,
            query_string: str,  # noqa: ARG001 - unused in the fake
            connection: object,  # noqa: ARG001 - unused in the fake
            eq_filters: dict[str, str] | None = None,
        ) -> list[dict[str, object]]:
            loads.append(eq_filters or {})
            # Both members belong to the same joint account, so each discovers
            # it and derives the same shared joint slice key.
            if table_name == str(table_names.TableNames.JOINT_ACCOUNTS):
                return [{"id": str(account)}]
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
            _JOINT,
        )
        repo_b = repository.payment_repository(
            "auth0|b",
            shared_cache,
            write_conn,
            _JOINT,
        )

        # Act - B warms its read, A writes a joint row, B reads again
        repo_b.get_all()
        joint_loads_before = loads.count(joint_filter)
        repo_a.apply(entities.BackendUpdates(added_rows=[{"id": str(uuid.uuid4())}]))
        repo_b.get_all()
        joint_loads_after = loads.count(joint_filter)

        # Assert - B's shared joint slice reloaded after A's write (was stale before)
        assert joint_loads_after == joint_loads_before + 1


class TestWriteStampsOwnership:
    """A repository stamps its own ownership onto every row it inserts.

    The grid add-row dialog builds a bare row that defaults to personal, so the
    repository — not the caller — is what makes a joint write land as joint.
    """

    @staticmethod
    def _captured_added_row(
        repo: repository.SupabaseRepository,
        monkeypatch: pytest.MonkeyPatch,
        added_row: dict,
    ) -> dict:
        """Apply one added row and return what reached ``client.update_backend``."""
        captured: dict[str, entities.BackendUpdates] = {}

        def _capture(
            table_name: str,  # noqa: ARG001 - only matches update_backend's signature
            updates: entities.BackendUpdates,
            conn: object,  # noqa: ARG001 - only matches update_backend's signature
        ) -> None:
            captured["updates"] = updates

        monkeypatch.setattr(repository.client, "update_backend", _capture)
        repo.apply(entities.BackendUpdates(added_rows=[added_row]))
        return captured["updates"].added_rows[0]

    def test_joint_add_is_stamped_joint_with_the_account_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange - a bare row defaulted to personal, as the add dialog builds it
        account = uuid.uuid4()
        cache = KeyedFakeCache({_JOINT_ACCOUNTS_KEY: [{"id": str(account)}]})
        repo = repository.bank_account_repository(_USER_ID, cache, _CONN, _JOINT)
        bare = _bank_view_row(ownership_type=_PERSONAL, joint_account_id=None)

        # Act
        written = self._captured_added_row(repo, monkeypatch, bare)

        # Assert - personal default overridden to joint, account id stamped
        assert all(
            [
                written["ownership_type"] == _JOINT,
                written["joint_account_id"] == str(account),
            ],
        )

    def test_personal_add_is_stamped_personal_with_no_account(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache([]),
            _CONN,
            _PERSONAL,
        )
        bare = _bank_view_row(ownership_type=_PERSONAL, joint_account_id=None)

        # Act
        written = self._captured_added_row(repo, monkeypatch, bare)

        # Assert
        assert all(
            [
                written["ownership_type"] == _PERSONAL,
                written["joint_account_id"] is None,
            ],
        )

    def test_no_ownership_table_add_is_left_untouched(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange - joint_accounts has no ownership dimension (ownership None)
        repo = repository.joint_account_repository(_USER_ID, FakeCache([]), _CONN)
        row = {"id": str(uuid.uuid4()), "name": "Our Joint"}

        # Act
        written = self._captured_added_row(repo, monkeypatch, row)

        # Assert - no ownership columns injected onto a table that lacks them
        assert "ownership_type" not in written


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
            _PERSONAL,
        )

        # Act
        result = repo.get_all()

        # Assert
        assert {type(p) for p in result} == {
            entities.ExpensePaymentModel,
            entities.IncomePaymentModel,
        }
