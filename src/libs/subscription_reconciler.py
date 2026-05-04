"""Reconciler for subscription-generated payments.

Ensures each active subscription has one future payment entry.
Once created, the user is free to edit the payment date or amount.
"""

import datetime
import enum

import st_supabase_connection
from dateutil import relativedelta

from libs import data_client
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, backend_updates_model


class CadenceDelta(enum.Enum):
    """Relativedelta values for each subscription cadence."""

    WEEKLY = relativedelta.relativedelta(weeks=1)
    MONTHLY = relativedelta.relativedelta(months=1)
    QUARTERLY = relativedelta.relativedelta(months=3)
    BIANNUALLY = relativedelta.relativedelta(months=6)
    YEARLY = relativedelta.relativedelta(years=1)


_PAYMENTS_TABLE = dfe_constants.TableNames.PAYMENTS.value
_SUBSCRIPTIONS_TABLE = dfe_constants.TableNames.SUBSCRIPTIONS.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
]


class SubscriptionReconciler:
    """Ensures each active subscription has a future payment entry.

    On app load, for each active subscription:
    - If no future payment exists, creates one for the next cadence date.
    - If a future payment already exists, leaves it untouched.

    For inactive subscriptions, deletes any future payments.
    Past payments are never modified.
    """

    def __init__(self) -> None:
        """Initialize the reconciler with today's date."""
        self._today = datetime.datetime.now(tz=datetime.UTC).date()

    def reconcile(
        self,
        connection: st_supabase_connection.SupabaseConnection = data_client.CONN,
    ) -> None:
        """Run the reconciliation pass."""
        subscriptions = data_client.get_data(
            table_name=_SUBSCRIPTIONS_TABLE,
            query_string="*",
            _connection=connection,
        )
        if not subscriptions:
            return

        validated_subs = [
            backend_models.SubscriptionModel.model_validate(sub)
            for sub in subscriptions
        ]

        existing_payment_data = data_client.get_data(
            table_name=_PAYMENTS_TABLE,
            query_string="*",
            _connection=connection,
        )
        existing_payments = [
            backend_models.ExpensePaymentModel.model_validate(payment)
            for payment in existing_payment_data
            if payment.get("subscription_id")
            and payment.get("payment_type") == "expense"
        ]
        payments_by_subscription = self._group_payments_by_subscription(
            existing_payments,
        )

        updates = backend_updates_model.BackendUpdates()

        for sub in validated_subs:
            sub_id = str(sub.id)
            current_payments = payments_by_subscription.get(sub_id, [])
            self._reconcile_subscription(sub, current_payments, updates)

        data_client.update_backend(
            table_name=_PAYMENTS_TABLE,
            updates=updates,
            tables_to_clear=_TABLES_TO_CLEAR,
            connection=connection,
        )

    def _reconcile_subscription(
        self,
        sub: backend_models.SubscriptionModel,
        current_payments: list[backend_models.ExpensePaymentModel],
        updates: backend_updates_model.BackendUpdates,
    ) -> None:
        """Reconcile a single subscription's payments."""
        future_payments = [
            payment
            for payment in current_payments
            if payment.payment_date >= self._today
        ]

        if not sub.is_active:
            updates.deleted_rows.extend(str(payment.id) for payment in future_payments)
            return

        # Delete future payments that fall after the subscription's end date
        if sub.end_date:
            expired = [
                payment
                for payment in future_payments
                if payment.payment_date > sub.end_date
            ]
            updates.deleted_rows.extend(str(payment.id) for payment in expired)
            future_payments = [
                payment
                for payment in future_payments
                if payment.payment_date <= sub.end_date
            ]

        # If a future payment already exists, leave it alone
        if future_payments:
            return

        # No future payment — create one for the next cadence date
        next_date = self._compute_next_date(sub)
        if next_date is None:
            return

        new_payment = backend_models.ExpensePaymentModel(
            user_id=sub.user_id,
            name=f"Sub: {sub.name}",
            expense=sub.amount,
            payment_date=next_date,
            bank_account_id=sub.bank_account_id,
            expense_source_id=sub.expense_source_id,
            subscription_id=sub.id,
        )
        updates.added_rows.append(new_payment.model_dump(mode="json"))

    def _compute_next_date(
        self,
        sub: backend_models.SubscriptionModel,
    ) -> datetime.date | None:
        """Compute the next payment date for a subscription from today onward."""
        try:
            delta = CadenceDelta[sub.cadence.upper()].value
        except KeyError:
            return None

        if sub.end_date and sub.end_date < self._today:
            return None

        current = sub.start_date
        while current < self._today:
            current += delta

        if sub.end_date and current > sub.end_date:
            return None

        return current

    @staticmethod
    def _group_payments_by_subscription(
        payments: list[backend_models.ExpensePaymentModel],
    ) -> dict[str, list[backend_models.ExpensePaymentModel]]:
        """Group payments by their subscription_id."""
        grouped: dict[str, list[backend_models.ExpensePaymentModel]] = {}
        for payment in payments:
            if payment.subscription_id:
                sub_id = str(payment.subscription_id)
                grouped.setdefault(sub_id, []).append(payment)
        return grouped
