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
from driven_adapters import errors
from driven_adapters.supabase import repository, table_names

_USER_ID = "auth0|test-user-123"
_CONN = mock.MagicMock(spec=st_supabase_connection.SupabaseConnection)


class FakeCache:
    """In-memory CacheGateway: serves fixed rows, records keys and invalidations."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        *,
        fail_fetch: bool = False,
    ) -> None:
        """Seed the fake with the rows a read should return."""
        self._rows = rows if rows is not None else []
        self.requested_keys: list[str] = []
        self.invalidated: list[str] = []
        self._fail_fetch = fail_fetch

    def get_from_or_load_cache(
        self,
        key: str,
        loader: Callable[[], list[dict[str, object]]],  # noqa: ARG002 - loader unused; the fake serves fixed rows without hitting a backend
    ) -> list[dict[str, object]]:
        self.requested_keys.append(key)
        if self._fail_fetch:
            msg = "fetch boom"
            raise RuntimeError(msg)
        return list(self._rows)

    def invalidate(self, keys: Iterable[str]) -> None:
        self.invalidated.extend(keys)


def _bank_view_row(
    *,
    user_id: str = _USER_ID,
    row_id: uuid.UUID | None = None,
    name: str = "Current",
    starting_balance: float = 250.0,
    current_balance: float = 250.0,
) -> dict:
    """Return a bank_accounts_view-shaped row (carries the computed column)."""
    return read_models.BankAccountView(
        id=row_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        starting_balance=starting_balance,
        current_balance=current_balance,
    ).model_dump(mode="json")


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

    def test_wraps_fetch_failure_in_adapter_error(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(
            _USER_ID,
            FakeCache(fail_fetch=True),
            _CONN,
        )

        # Act / Assert
        with pytest.raises(errors.AdapterError, match="Failed to fetch rows"):
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
# Writes: persistence + invalidation fan-out
# ---------------------------------------------------------------------------


class TestSave:
    def test_persists_the_row_to_the_write_table(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(_USER_ID, FakeCache(), _CONN)
        account = entities.BankAccountModel(user_id=_USER_ID, name="New")

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.save(account)

        # Assert
        table, updates, conn = mock_update.call_args.args
        assert all(
            [
                table == str(table_names.TableNames.BANK_ACCOUNTS),
                updates.added_rows == [account.model_dump(mode="json")],
                conn is _CONN,
            ],
        )

    def test_wraps_write_failure_in_adapter_error(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(_USER_ID, FakeCache(), _CONN)

        # Act / Assert
        with (
            mock.patch.object(
                repository.client,
                "update_backend",
                side_effect=RuntimeError("write boom"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to save row"),
        ):
            repo.save(entities.BankAccountModel(user_id=_USER_ID, name="New"))


class TestApply:
    def test_persists_a_non_empty_batch(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(_USER_ID, FakeCache(), _CONN)
        updates = entities.BackendUpdates(deleted_rows=[str(uuid.uuid4())])

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.apply(updates)

        # Assert
        mock_update.assert_called_once_with(
            str(table_names.TableNames.BANK_ACCOUNTS),
            updates,
            _CONN,
        )

    def test_skips_an_empty_batch(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(_USER_ID, FakeCache(), _CONN)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.apply(entities.BackendUpdates())

        # Assert
        mock_update.assert_not_called()

    def test_wraps_write_failure_in_adapter_error(self) -> None:
        # Arrange
        repo = repository.bank_account_repository(_USER_ID, FakeCache(), _CONN)
        updates = entities.BackendUpdates(added_rows=[{"id": "x"}])

        # Act / Assert
        with (
            mock.patch.object(
                repository.client,
                "update_backend",
                side_effect=RuntimeError("write boom"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to apply updates"),
        ):
            repo.apply(updates)


class TestInvalidation:
    def test_write_busts_the_table_and_its_dependent_view_keys(self) -> None:
        # Arrange - expense sources fan out to the expense and budget views
        cache = FakeCache()
        repo = repository.expense_source_repository(_USER_ID, cache, _CONN)
        updates = entities.BackendUpdates(added_rows=[{"id": "x"}])

        # Act
        with mock.patch.object(repository.client, "update_backend"):
            repo.apply(updates)

        # Assert - every affected key is user-scoped
        expected = {
            f"{_USER_ID}:{table_names.TableNames.EXPENSE_SOURCES}",
            f"{_USER_ID}:{table_names.ViewNames.EXPENSE_SOURCES}",
            f"{_USER_ID}:{table_names.ViewNames.BUDGET_TRACKER}",
        }
        assert set(cache.invalidated) == expected


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


# ---------------------------------------------------------------------------
# Payments: discriminated-union parsing
# ---------------------------------------------------------------------------


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
