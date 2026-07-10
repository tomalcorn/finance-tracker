"""Unit tests for the generic Supabase repository.

Reads and writes are exercised through an in-memory ``FakeCache`` that stands
in for the injected ``CacheGateway`` — the repository never touches the
Supabase client directly.
"""

import uuid

import pytest

from domain import entities, read_models
from driven_adapters import errors
from driven_adapters.supabase import repository, table_names

_USER_ID = "auth0|test-user-123"
_OTHER_USER_ID = "auth0|other-user-456"


class FakeCache:
    """In-memory CacheGateway: serves fixed rows and records writes."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        *,
        fail_fetch: bool = False,
        fail_write: bool = False,
    ) -> None:
        """Seed the fake with the rows a read should return."""
        self._rows = rows if rows is not None else []
        self.writes: list[tuple[str, entities.BackendUpdates]] = []
        self._fail_fetch = fail_fetch
        self._fail_write = fail_write

    def fetch(self, table: str) -> list[dict]:  # noqa: ARG002 - table unused by fake
        if self._fail_fetch:
            msg = "fetch boom"
            raise RuntimeError(msg)
        return list(self._rows)

    def write(self, table: str, updates: entities.BackendUpdates) -> None:
        if self._fail_write:
            msg = "write boom"
            raise RuntimeError(msg)
        self.writes.append((table, updates))


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
# Reads: parsing + user scoping
# ---------------------------------------------------------------------------


class TestGetAll:
    def test_parses_rows_and_scopes_to_current_user(self) -> None:
        mine = _bank_view_row(user_id=_USER_ID, name="Mine")
        theirs = _bank_view_row(user_id=_OTHER_USER_ID, name="Theirs")
        repo = repository.bank_account_repository(_USER_ID, FakeCache([mine, theirs]))

        result = repo.get_all()

        assert [m.name for m in result] == ["Mine"]
        assert all(isinstance(m, entities.BankAccountModel) for m in result)

    def test_wraps_fetch_failure_in_adapter_error(self) -> None:
        repo = repository.bank_account_repository(_USER_ID, FakeCache(fail_fetch=True))
        with pytest.raises(errors.AdapterError, match="Failed to fetch rows"):
            repo.get_all()


class TestGetByIds:
    def test_returns_only_matching_ids(self) -> None:
        wanted = uuid.uuid4()
        rows = [
            _bank_view_row(row_id=wanted, name="Wanted"),
            _bank_view_row(name="Other"),
        ]
        repo = repository.bank_account_repository(_USER_ID, FakeCache(rows))

        result = repo.get_by_ids([wanted])

        assert [m.id for m in result] == [wanted]


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


class TestSave:
    def test_writes_the_row_to_the_write_table(self) -> None:
        cache = FakeCache()
        repo = repository.bank_account_repository(_USER_ID, cache)
        account = entities.BankAccountModel(user_id=_USER_ID, name="New")

        repo.save(account)

        assert len(cache.writes) == 1
        table, updates = cache.writes[0]
        assert table == table_names.TableNames.BANK_ACCOUNTS
        assert updates.added_rows == [account.model_dump(mode="json")]

    def test_wraps_write_failure_in_adapter_error(self) -> None:
        repo = repository.bank_account_repository(_USER_ID, FakeCache(fail_write=True))
        with pytest.raises(errors.AdapterError, match="Failed to save row"):
            repo.save(entities.BankAccountModel(user_id=_USER_ID, name="New"))


class TestApply:
    def test_writes_a_non_empty_batch(self) -> None:
        cache = FakeCache()
        repo = repository.bank_account_repository(_USER_ID, cache)
        updates = entities.BackendUpdates(deleted_rows=[str(uuid.uuid4())])

        repo.apply(updates)

        assert cache.writes == [(table_names.TableNames.BANK_ACCOUNTS, updates)]

    def test_skips_an_empty_batch(self) -> None:
        cache = FakeCache()
        repo = repository.bank_account_repository(_USER_ID, cache)

        repo.apply(entities.BackendUpdates())

        assert cache.writes == []

    def test_wraps_write_failure_in_adapter_error(self) -> None:
        repo = repository.bank_account_repository(_USER_ID, FakeCache(fail_write=True))
        updates = entities.BackendUpdates(added_rows=[{"id": "x"}])
        with pytest.raises(errors.AdapterError, match="Failed to apply updates"):
            repo.apply(updates)


# ---------------------------------------------------------------------------
# GridDataSource surface
# ---------------------------------------------------------------------------


class TestRows:
    def test_returns_view_models_with_computed_columns(self) -> None:
        balance = 999.0
        row = _bank_view_row(current_balance=balance)
        repo = repository.bank_account_repository(_USER_ID, FakeCache([row]))

        result = repo.rows()

        assert len(result) == 1
        view = result[0]
        assert isinstance(view, read_models.BankAccountView)
        assert view.current_balance == balance


class TestUniqueValues:
    def test_dedups_and_drops_nulls(self) -> None:
        rows = [
            {"user_id": _USER_ID, "name": "A", "note": "x"},
            {"user_id": _USER_ID, "name": "A", "note": None},
            {"user_id": _USER_ID, "name": "B", "note": "y"},
        ]
        repo = repository.bank_account_repository(_USER_ID, FakeCache(rows))

        assert repo.unique_values("name") == {"A", "B"}
        assert repo.unique_values("note") == {"x", "y"}


# ---------------------------------------------------------------------------
# Payments: discriminated-union parsing
# ---------------------------------------------------------------------------


class TestPaymentRepository:
    def test_get_all_parses_expense_and_income_into_correct_subtypes(self) -> None:
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
        repo = repository.payment_repository(_USER_ID, FakeCache([expense, income]))

        result = repo.get_all()

        assert {type(p) for p in result} == {
            entities.ExpensePaymentModel,
            entities.IncomePaymentModel,
        }
