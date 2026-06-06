"""Integration tests for SubscriptionReconciler against the test Supabase DB."""

import datetime
import typing
import uuid

import pytest
import st_supabase_connection

from libs import data_client
from libs.models import backend_models
from libs.subscription_reconciler import SubscriptionReconciler

_SUBSCRIPTIONS = "subscriptions"
_PAYMENTS = "payments"
_BANK_ACCOUNTS = "bank_accounts"


@pytest.fixture(name="user_and_bank")
def _user_and_bank(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[tuple[str, uuid.UUID], None, None]:
    """Create a bank account for FK constraints, clean up after."""
    user_id = "auth0|int-test-user"
    bank = backend_models.BankAccountModel(user_id=user_id, name="Test Account")

    connection.table(_BANK_ACCOUNTS).insert(bank.model_dump(mode="json")).execute()

    yield user_id, bank.id

    # Clean up — cascade handles payments/subscriptions
    connection.table(_PAYMENTS).delete().eq("user_id", str(user_id)).execute()
    connection.table(_SUBSCRIPTIONS).delete().eq("user_id", str(user_id)).execute()
    connection.table(_BANK_ACCOUNTS).delete().eq("id", str(bank.id)).execute()
    data_client._get_data_cached.clear()


def _insert_subscription(
    connection: st_supabase_connection.SupabaseConnection,
    sub: backend_models.SubscriptionModel,
) -> None:
    connection.table(_SUBSCRIPTIONS).insert(
        sub.model_dump(mode="json"),
    ).execute()


def _insert_payment(
    connection: st_supabase_connection.SupabaseConnection,
    payment: backend_models.ExpensePaymentModel,
) -> None:
    connection.table(_PAYMENTS).insert(
        payment.model_dump(mode="json"),
    ).execute()


def _get_payments_for_sub(
    connection: st_supabase_connection.SupabaseConnection,
    subscription_id: uuid.UUID,
) -> list[backend_models.ExpensePaymentModel]:
    data_client._get_data_cached.clear()
    rows = (
        connection.table(_PAYMENTS)
        .select("*")
        .eq("subscription_id", str(subscription_id))
        .execute()
        .data
    )
    return [backend_models.ExpensePaymentModel.model_validate(row) for row in rows]


def _run_reconcile(
    connection: st_supabase_connection.SupabaseConnection,
) -> None:
    """Run the reconciler with the test connection injected."""
    data_client._get_data_cached.clear()
    SubscriptionReconciler().reconcile(connection=connection)
    data_client._get_data_cached.clear()


class TestReconcileIntegration:
    """Integration tests for SubscriptionReconciler against the real DB."""

    def test_creates_payment_for_active_subscription(
        self,
        connection: st_supabase_connection.SupabaseConnection,
        user_and_bank: tuple[str, uuid.UUID],
    ) -> None:
        """Active sub with no payments should produce one payment."""
        user_id, bank_id = user_and_bank
        sub = backend_models.SubscriptionModel(
            user_id=user_id,
            name="Netflix",
            amount=15.99,
            cadence="monthly",
            bank_account_id=bank_id,
            start_date=datetime.date(2026, 1, 1),
            is_active=True,
        )
        _insert_subscription(connection, sub)

        _run_reconcile(connection)

        payments = _get_payments_for_sub(connection, sub.id)
        assert all(
            [
                len(payments) == 1,
                payments[0].name == "Sub: Netflix",
            ],
        )

    def test_does_not_duplicate_existing_future_payment(
        self,
        connection: st_supabase_connection.SupabaseConnection,
        user_and_bank: tuple[str, uuid.UUID],
    ) -> None:
        """Running reconcile twice should not create a second payment."""
        user_id, bank_id = user_and_bank
        sub = backend_models.SubscriptionModel(
            user_id=user_id,
            name="Spotify",
            amount=9.99,
            cadence="monthly",
            bank_account_id=bank_id,
            start_date=datetime.date(2026, 1, 1),
            is_active=True,
        )
        _insert_subscription(connection, sub)

        _run_reconcile(connection)
        _run_reconcile(connection)

        payments = _get_payments_for_sub(connection, sub.id)
        assert len(payments) == 1

    def test_deletes_future_payment_for_inactive_subscription(
        self,
        connection: st_supabase_connection.SupabaseConnection,
        user_and_bank: tuple[str, uuid.UUID],
    ) -> None:
        """Deactivating a sub should remove its future payment."""
        user_id, bank_id = user_and_bank
        sub = backend_models.SubscriptionModel(
            user_id=user_id,
            name="HBO",
            amount=14.99,
            cadence="monthly",
            bank_account_id=bank_id,
            start_date=datetime.date(2026, 1, 1),
            is_active=True,
        )
        _insert_subscription(connection, sub)

        # First reconcile creates the payment
        _run_reconcile(connection)
        payments_before = _get_payments_for_sub(connection, sub.id)
        assert len(payments_before) == 1

        # Deactivate the subscription
        connection.table(_SUBSCRIPTIONS).update(
            {"is_active": False},
        ).eq("id", str(sub.id)).execute()

        # Second reconcile should delete the future payment
        _run_reconcile(connection)
        payments_after = _get_payments_for_sub(connection, sub.id)
        assert len(payments_after) == 0

    def test_deletes_payment_past_end_date(
        self,
        connection: st_supabase_connection.SupabaseConnection,
        user_and_bank: tuple[str, uuid.UUID],
    ) -> None:
        """A future payment beyond the sub's end_date should be removed."""
        user_id, bank_id = user_and_bank
        today = datetime.datetime.now(tz=datetime.UTC).date()
        end_date = today + datetime.timedelta(days=30)
        sub = backend_models.SubscriptionModel(
            user_id=user_id,
            name="Trial Sub",
            amount=5.00,
            cadence="monthly",
            bank_account_id=bank_id,
            start_date=today,
            end_date=end_date,
            is_active=True,
        )
        _insert_subscription(connection, sub)

        # Manually insert a future payment beyond end_date
        future_payment = backend_models.ExpensePaymentModel(
            user_id=user_id,
            name="Sub: Trial Sub",
            expense=5.00,
            payment_date=end_date + datetime.timedelta(days=30),
            bank_account_id=bank_id,
            subscription_id=sub.id,
        )
        _insert_payment(connection, future_payment)

        _run_reconcile(connection)

        # The invalid payment (past end_date) is deleted,
        # but a valid one is created for the next cadence date before end_date
        payments = _get_payments_for_sub(connection, sub.id)
        assert sub.end_date is not None
        assert all(
            [
                len(payments) == 1,
                payments[0].payment_date <= sub.end_date,
            ],
        )
