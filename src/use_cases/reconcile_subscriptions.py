"""Use case for reconciling subscription-generated payments."""

import datetime
import enum

from dateutil import relativedelta

from domain import entities
from domain import errors as domain_errors
from ports import repository
from use_cases import errors


class CadenceDelta(enum.Enum):
    """Relativedelta values for each subscription cadence."""

    WEEKLY = relativedelta.relativedelta(weeks=1)
    MONTHLY = relativedelta.relativedelta(months=1)
    QUARTERLY = relativedelta.relativedelta(months=3)
    BIANNUALLY = relativedelta.relativedelta(months=6)
    YEARLY = relativedelta.relativedelta(years=1)


class ReconcileSubscriptionsUseCase:
    """Ensures each active subscription has a future payment entry.

    On app load, for each subscription:
    - If active and no future payment exists, creates one for the next cadence date.
    - If a future payment already exists, leaves it untouched.
    - For inactive subscriptions, deletes any future payments.

    Past payments are never modified.
    """

    def __init__(
        self,
        subscription_repo: repository.SubscriptionRepository,
        payment_repo: repository.PaymentRepository,
        *,
        today: datetime.date | None = None,
    ) -> None:
        """Initialise with repository ports and an optional reference date."""
        self._subscription_repo = subscription_repo
        self._payment_repo = payment_repo
        self._today = today or datetime.datetime.now(tz=datetime.UTC).date()

    def execute(self) -> None:
        """Run the reconciliation pass.

        Raises:
            InvalidCadenceError: if the provided cadence is not known.

        """
        subscriptions = self._subscription_repo.get_all()
        if not subscriptions:
            return

        existing_payments = [
            payment
            for payment in self._payment_repo.get_all()
            if isinstance(payment, entities.ExpensePaymentModel)
            and payment.subscription_id is not None
        ]
        payments_by_subscription = self._group_payments_by_subscription(
            existing_payments,
        )

        updates = entities.BackendUpdates()

        for sub in subscriptions:
            sub_id = str(sub.id)
            current_payments = payments_by_subscription.get(sub_id, [])
            try:
                self._reconcile_subscription(sub, current_payments, updates)
            except domain_errors.InvalidSubscriptionCadenceError as e:
                raise errors.InvalidCadenceError(e.cadence) from e

        if updates.added_rows or updates.deleted_rows:
            self._payment_repo.apply_updates(updates)

    def _reconcile_subscription(
        self,
        sub: entities.SubscriptionModel,
        current_payments: list[entities.ExpensePaymentModel],
        updates: entities.BackendUpdates,
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

        if future_payments:
            return

        next_date = self._compute_next_date(sub)
        if next_date is None:
            return

        new_payment = entities.ExpensePaymentModel(
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
        sub: entities.SubscriptionModel,
    ) -> datetime.date | None:
        """Compute the next payment date for a subscription from today onward.

        Raises:
            InvalidSubscriptionCadenceError: if the provided cadence is not known.

        """
        try:
            cadence = sub.cadence.upper()
            delta = CadenceDelta[sub.cadence.upper()].value
        except KeyError as e:
            raise domain_errors.InvalidSubscriptionCadenceError(cadence) from e

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
        payments: list[entities.ExpensePaymentModel],
    ) -> dict[str, list[entities.ExpensePaymentModel]]:
        """Group payments by their subscription_id."""
        grouped: dict[str, list[entities.ExpensePaymentModel]] = {}
        for payment in payments:
            if payment.subscription_id:
                sub_id = str(payment.subscription_id)
                grouped.setdefault(sub_id, []).append(payment)
        return grouped
