"""Unit tests for Supabase repository adapters."""

import datetime
import uuid
from unittest import mock

import pytest
import st_supabase_connection

from domain import entities
from driven_adapters import errors
from driven_adapters.supabase import repository, table_names

_USER_ID = "auth0|test-user-123"
_OTHER_USER_ID = "auth0|other-user-456"


@pytest.fixture(name="user_id")
def _user_id() -> str:
    return _USER_ID


@pytest.fixture(name="mock_connection")
def _mock_connection() -> mock.MagicMock:
    return mock.MagicMock(spec=st_supabase_connection.SupabaseConnection)


@pytest.fixture(name="bank_account_id")
def _bank_account_id() -> uuid.UUID:
    return uuid.uuid4()


def _bank_account_row(
    *,
    user_id: str = _USER_ID,
    account_id: uuid.UUID | None = None,
    name: str = "Current Account",
    starting_balance: float = 250.0,
) -> dict:
    return entities.BankAccountModel(
        id=account_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        starting_balance=starting_balance,
    ).model_dump(mode="json")


def _bank_account_repo(
    mock_connection: mock.MagicMock,
    user_id: str = _USER_ID,
) -> repository.SupabaseBankAccountRepository:
    return repository.SupabaseBankAccountRepository(mock_connection, user_id)


class TestFetchRows:
    """Tests for SupabaseRepositoryBase._fetch_rows."""

    def test_filters_rows_to_current_user(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        own_row = _bank_account_row(user_id=user_id, name="Mine")
        other_row = _bank_account_row(user_id=_OTHER_USER_ID, name="Theirs")
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(
            repository.client,
            "fetch_table",
            return_value=[own_row, other_row],
        ):
            rows = repo._fetch_rows()

        # Assert
        assert all(
            [
                len(rows) == 1,
                rows[0]["name"] == "Mine",
                rows[0]["user_id"] == user_id,
            ],
        )

    def test_raises_adapter_error_when_get_data_fails(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act/Assert
        with (
            mock.patch.object(
                repository.client,
                "fetch_table",
                side_effect=RuntimeError("network down"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to fetch rows"),
        ):
            repo._fetch_rows()


class TestFetchById:
    """Tests for SupabaseRepositoryBase._fetch_by_id."""

    def test_returns_matching_row(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        row = _bank_account_row(user_id=user_id, account_id=bank_account_id)
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(
            repository.client,
            "fetch_table",
            return_value=[row],
        ):
            result = repo._fetch_by_id(bank_account_id)

        # Assert
        assert result == row

    def test_returns_none_when_not_found(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=[]):
            result = repo._fetch_by_id(uuid.uuid4())

        # Assert
        assert result is None


class TestFetchByIds:
    """Tests for SupabaseRepositoryBase._fetch_by_ids."""

    def test_returns_matching_rows(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        first_id = uuid.uuid4()
        second_id = uuid.uuid4()
        rows = [
            _bank_account_row(user_id=user_id, account_id=first_id, name="First"),
            _bank_account_row(user_id=user_id, account_id=second_id, name="Second"),
            _bank_account_row(user_id=user_id, name="Other"),
        ]
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo._fetch_by_ids([first_id, second_id])

        # Assert
        returned_ids = {r["id"] for r in result}
        expected_result_len = 2
        assert all(
            [
                len(result) == expected_result_len,
                str(first_id) in returned_ids,
                str(second_id) in returned_ids,
            ],
        )


class TestSaveOne:
    """Tests for SupabaseRepositoryBase._save_one."""

    def test_calls_update_backend_with_row(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        row = _bank_account_row(user_id=user_id)
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo._save_one(row)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.BANK_ACCOUNTS,
            entities.BackendUpdates(added_rows=[row]),
            connection=mock_connection,
        )

    def test_raises_adapter_error_on_failure(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act/Assert
        with (
            mock.patch.object(
                repository.client,
                "update_backend",
                side_effect=RuntimeError("write failed"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to save row"),
        ):
            repo._save_one(_bank_account_row(user_id=user_id))


class TestSaveMany:
    """Tests for SupabaseRepositoryBase._save_many."""

    def test_calls_update_backend_with_all_rows(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        rows = [
            _bank_account_row(user_id=user_id, name="First"),
            _bank_account_row(user_id=user_id, name="Second"),
        ]
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo._save_many(rows)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.BANK_ACCOUNTS,
            entities.BackendUpdates(added_rows=rows),
            connection=mock_connection,
        )

    def test_raises_adapter_error_on_failure(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act/Assert
        with (
            mock.patch.object(
                repository.client,
                "update_backend",
                side_effect=RuntimeError("bulk write failed"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to bulk-save rows"),
        ):
            repo._save_many([_bank_account_row(user_id=user_id)])


class TestDeleteById:
    """Tests for SupabaseRepositoryBase._delete_by_id."""

    def test_calls_update_backend_with_deleted_id(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo._delete_by_id(bank_account_id)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.BANK_ACCOUNTS,
            entities.BackendUpdates(deleted_rows=[str(bank_account_id)]),
            connection=mock_connection,
        )

    def test_raises_adapter_error_on_failure(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act/Assert
        with (
            mock.patch.object(
                repository.client,
                "update_backend",
                side_effect=RuntimeError("delete failed"),
            ),
            pytest.raises(errors.AdapterError, match="Failed to delete row"),
        ):
            repo._delete_by_id(bank_account_id)


class TestBankAccountRepository:
    """Tests for SupabaseBankAccountRepository public API."""

    def test_get_all_returns_models_for_current_user(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        rows = [
            _bank_account_row(user_id=user_id, name="First"),
            _bank_account_row(user_id=_OTHER_USER_ID, name="Other"),
        ]
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_all()

        # Assert
        assert all(
            [
                len(result) == 1,
                isinstance(result[0], entities.BankAccountModel),
                result[0].name == "First",
                result[0].user_id == user_id,
            ],
        )

    def test_get_by_id_returns_model_when_found(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        row = _bank_account_row(
            user_id=user_id,
            account_id=bank_account_id,
            name="Savings",
        )
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=[row]):
            result = repo.get_by_id(bank_account_id)

        # Assert
        assert all(
            [
                isinstance(result, entities.BankAccountModel),
                result is not None and result.id == bank_account_id,
                result.name == "Savings",  # ty:ignore[unresolved-attribute] - asserted above
            ],
        )

    def test_get_by_id_returns_none_when_not_found(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=[]):
            result = repo.get_by_id(uuid.uuid4())

        # Assert
        assert result is None

    def test_save_persists_model_dump(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        account = entities.BankAccountModel(
            user_id=user_id,
            name="New Account",
            starting_balance=500.0,
        )
        repo = _bank_account_repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.save(account)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.BANK_ACCOUNTS,
            entities.BackendUpdates(added_rows=[account.model_dump(mode="json")]),
            connection=mock_connection,
        )


class TestBudgetTrackerRepository:
    """Tests for SupabaseBudgetTrackerRepository."""

    def _repo(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> repository.SupabaseBudgetTrackerRepository:
        return repository.SupabaseBudgetTrackerRepository(mock_connection, user_id)

    def _item_row(
        self,
        *,
        user_id: str,
        item_id: uuid.UUID | None = None,
        name: entities.BudgetTrackerName = entities.BudgetTrackerName.EXPENSES,
    ) -> dict:
        return entities.BudgetTrackerItemModel(
            id=item_id or uuid.uuid4(),
            user_id=user_id,
            name=name,
            total_budget=100.0,
        ).model_dump(mode="json")

    def test_get_by_ids_returns_matching_items(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        first_id = uuid.uuid4()
        second_id = uuid.uuid4()
        rows = [
            self._item_row(user_id=user_id, item_id=first_id),
            self._item_row(
                user_id=user_id,
                item_id=second_id,
                name=entities.BudgetTrackerName.SAVINGS,
            ),
            self._item_row(user_id=user_id, name=entities.BudgetTrackerName.JOINT),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_by_ids([first_id, second_id])

        # Assert
        returned_ids = {item.id for item in result}
        expected_result_len = 2
        assert all(
            [
                len(result) == expected_result_len,
                first_id in returned_ids,
                second_id in returned_ids,
            ],
        )

    def test_save_many_persists_all_items(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> None:
        # Arrange
        items = [
            entities.BudgetTrackerItemModel(
                user_id=user_id,
                name=entities.BudgetTrackerName.EXPENSES,
            ),
            entities.BudgetTrackerItemModel(
                user_id=user_id,
                name=entities.BudgetTrackerName.SAVINGS,
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.save_many(items)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.BUDGET_TRACKER,
            entities.BackendUpdates(
                added_rows=[item.model_dump(mode="json") for item in items],
            ),
            connection=mock_connection,
        )


class TestSubscriptionRepository:
    """Tests for SupabaseSubscriptionRepository."""

    def _repo(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> repository.SupabaseSubscriptionRepository:
        return repository.SupabaseSubscriptionRepository(mock_connection, user_id)

    def _subscription_row(
        self,
        *,
        user_id: str,
        bank_account_id: uuid.UUID,
        is_active: bool,
        name: str,
    ) -> dict:
        return entities.SubscriptionModel(
            user_id=user_id,
            name=name,
            bank_account_id=bank_account_id,
            is_active=is_active,
        ).model_dump(mode="json")

    def test_get_active_returns_only_active_subscriptions(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        rows = [
            self._subscription_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
                is_active=True,
                name="Active",
            ),
            self._subscription_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
                is_active=False,
                name="Inactive",
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_active()

        # Assert
        assert all(
            [
                len(result) == 1,
                result[0].name == "Active",
                result[0].is_active is True,
            ],
        )


class TestPaymentRepository:
    """Tests for SupabasePaymentRepository."""

    def _repo(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
    ) -> repository.SupabasePaymentRepository:
        return repository.SupabasePaymentRepository(mock_connection, user_id)

    def _expense_payment_row(
        self,
        *,
        user_id: str,
        bank_account_id: uuid.UUID,
        subscription_id: uuid.UUID | None = None,
        name: str = "Groceries",
    ) -> dict:
        return entities.ExpensePaymentModel(
            user_id=user_id,
            name=name,
            expense=42.0,
            bank_account_id=bank_account_id,
            subscription_id=subscription_id,
        ).model_dump(mode="json")

    def _income_payment_row(
        self,
        *,
        user_id: str,
        bank_account_id: uuid.UUID,
        name: str = "Salary",
    ) -> dict:
        return entities.IncomePaymentModel(
            user_id=user_id,
            name=name,
            income=3000.0,
            bank_account_id=bank_account_id,
        ).model_dump(mode="json")

    def test_get_all_parses_expense_and_income_payments(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        rows = [
            self._expense_payment_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
            ),
            self._income_payment_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_all()

        # Assert
        expected_result_len = 2
        assert all(
            [
                len(result) == expected_result_len,
                isinstance(result[0], entities.ExpensePaymentModel),
                isinstance(result[1], entities.IncomePaymentModel),
                result[0].payment_type == "expense",
                result[1].payment_type == "income",
            ],
        )

    @pytest.mark.parametrize(
        ("target_account_id", "other_account_id", "expected_name"),
        [
            pytest.param(
                uuid.UUID("00000000-0000-0000-0000-000000000001"),
                uuid.UUID("00000000-0000-0000-0000-000000000002"),
                "Target",
                id="first_account",
            ),
            pytest.param(
                uuid.UUID("00000000-0000-0000-0000-000000000003"),
                uuid.UUID("00000000-0000-0000-0000-000000000004"),
                "Other target",
                id="second_account",
            ),
        ],
    )
    def test_get_by_bank_account_filters_by_account_id(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        target_account_id: uuid.UUID,
        other_account_id: uuid.UUID,
        expected_name: str,
    ) -> None:
        # Arrange
        rows = [
            self._expense_payment_row(
                user_id=user_id,
                bank_account_id=target_account_id,
                name=expected_name,
            ),
            self._expense_payment_row(
                user_id=user_id,
                bank_account_id=other_account_id,
                name="Other",
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_by_bank_account(target_account_id)

        # Assert
        assert all(
            [
                len(result) == 1,
                result[0].name == expected_name,
                result[0].bank_account_id == target_account_id,
            ],
        )

    @pytest.mark.parametrize(
        ("target_subscription_id", "other_subscription_id"),
        [
            pytest.param(uuid.uuid4(), uuid.uuid4(), id="random_ids"),
            pytest.param(
                uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                id="fixed_ids",
            ),
        ],
    )
    def test_get_by_subscription_filters_by_subscription_id(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
        target_subscription_id: uuid.UUID,
        other_subscription_id: uuid.UUID,
    ) -> None:
        # Arrange
        rows = [
            self._expense_payment_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
                subscription_id=target_subscription_id,
                name="Sub payment",
            ),
            self._expense_payment_row(
                user_id=user_id,
                bank_account_id=bank_account_id,
                subscription_id=other_subscription_id,
                name="Other sub",
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "fetch_table", return_value=rows):
            result = repo.get_by_subscription(target_subscription_id)

        # Assert
        assert all(
            [
                len(result) == 1,
                result[0].name == "Sub payment",
                result[0].subscription_id == target_subscription_id,
            ],
        )

    def test_save_many_persists_all_payments(
        self,
        mock_connection: mock.MagicMock,
        user_id: str,
        bank_account_id: uuid.UUID,
    ) -> None:
        # Arrange
        payments: list[entities.AnyPaymentModel] = [
            entities.ExpensePaymentModel(
                user_id=user_id,
                name="Rent",
                expense=1200.0,
                payment_date=datetime.date(2026, 6, 1),
                bank_account_id=bank_account_id,
            ),
            entities.IncomePaymentModel(
                user_id=user_id,
                name="Pay",
                income=2500.0,
                payment_date=datetime.date(2026, 6, 1),
                bank_account_id=bank_account_id,
            ),
        ]
        repo = self._repo(mock_connection, user_id)

        # Act
        with mock.patch.object(repository.client, "update_backend") as mock_update:
            repo.save_many(payments)

        # Assert
        mock_update.assert_called_once_with(
            table_names.TableNames.PAYMENTS,
            entities.BackendUpdates(
                added_rows=[payment.model_dump(mode="json") for payment in payments],
            ),
            connection=mock_connection,
        )
