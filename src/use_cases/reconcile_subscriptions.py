"""Use case for reconciling subscription-generated payments."""

import dataclasses
import datetime
import enum
from typing import TYPE_CHECKING

from dateutil import relativedelta

from domain import entities
from domain import errors as domain_errors
from use_cases import errors, linked_payments

if TYPE_CHECKING:
    from ports import repository

    type PaymentRepository = repository.Repository[entities.AnyPaymentModel]


class CadenceDelta(enum.Enum):
    """Relativedelta values for each subscription cadence."""

    WEEKLY = relativedelta.relativedelta(weeks=1)
    MONTHLY = relativedelta.relativedelta(months=1)
    QUARTERLY = relativedelta.relativedelta(months=3)
    BIANNUALLY = relativedelta.relativedelta(months=6)
    YEARLY = relativedelta.relativedelta(years=1)


def _as_expense(payment: entities.AnyPaymentModel) -> entities.ExpensePaymentModel:
    """Narrow a built payment to the expense arm of the union."""
    if not isinstance(payment, entities.ExpensePaymentModel):
        msg = f"expected an expense payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


def _as_income(payment: entities.AnyPaymentModel) -> entities.IncomePaymentModel:
    """Narrow a built payment to the income arm of the union."""
    if not isinstance(payment, entities.IncomePaymentModel):
        msg = f"expected an income payment, got {type(payment).__name__}"
        raise TypeError(msg)
    return payment


@dataclasses.dataclass(frozen=True)
class _ContributionPlan:
    """What one joint-contribution subscription needs settled on both sides."""

    sub: entities.SubscriptionModel
    due: list[entities.RawRow]
    superseded: set[str]
    current_payments: list[entities.ExpensePaymentModel]


class ReconcileSubscriptionsUseCase:
    """Ensures each active subscription has a future payment entry.

    On app load, for each subscription:
    - If active and no future payment exists, creates one for the next cadence date.
    - If a future payment already exists, leaves it untouched.
    - For inactive subscriptions, deletes any future payments.

    Past payments are never modified.

    A subscription that is a **joint contribution** books a linked pair instead
    of a lone expense — the same pair the Contribute action books — so the money
    leaving the personal ledger arrives in the joint one. Only a personal
    instance does that: it is handed a joint payments repository, and a joint
    instance is not, because a joint-owned subscription must never spawn a
    contribution.
    """

    def __init__(
        self,
        subscription_repo: "repository.Repository[entities.SubscriptionModel]",
        payment_repo: "repository.Repository[entities.AnyPaymentModel]",
        *,
        joint_payment_repo: "PaymentRepository | None" = None,
        today: datetime.date | None = None,
    ) -> None:
        """Initialise with repository ports and an optional reference date.

        Args:
            subscription_repo: The subscriptions to reconcile.
            payment_repo: Payments in this instance's own ownership mode.
            joint_payment_repo: Payments in joint mode, for the income leg of a
                contribution. Omitted on a joint instance, which leaves any
                contribution it somehow reads untouched rather than booking half
                of it.
            today: The reference date reconciliation runs against.

        """
        self._subscription_repo = subscription_repo
        self._payment_repo = payment_repo
        self._joint_payment_repo = joint_payment_repo
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

        new_rows: list[entities.RawRow] = []
        deleted_ids: list[str] = []
        contributions: list[_ContributionPlan] = []

        for sub in subscriptions:
            sub_id = str(sub.id)
            current_payments = payments_by_subscription.get(sub_id, [])
            try:
                due, superseded = self._reconcile_subscription(sub, current_payments)
            except domain_errors.InvalidSubscriptionCadenceError as e:
                raise errors.InvalidCadenceError(e.cadence) from e
            if sub.is_joint_contribution:
                contributions.append(
                    _ContributionPlan(sub, due, set(superseded), current_payments),
                )
                continue
            new_rows.extend(due)
            deleted_ids.extend(superseded)

        self._payment_repo.save_entities(self._payment_repo.build_entities(new_rows))
        self._payment_repo.apply_deletions(deleted_ids)
        self._settle_contributions(contributions)

    def _settle_contributions(self, plans: list[_ContributionPlan]) -> None:
        """Settle each contribution subscription on both sides of the ledger.

        Kept out of the batched personal write above because a contribution is
        three ordered writes per payment, not one row in a batch — and because
        both of its legs have to move together: deleting only the expense would
        leave an orphaned income sitting in the shared books
        (``linked_payment_id`` is ``ON DELETE SET NULL``, so nothing else would
        remove it).

        The joint incomes are read once, keyed by the expense each points back
        at, and answer every question this pass asks: which income to delete
        alongside a superseded expense, and whether a future expense already has
        the income it is supposed to have.
        """
        joint_repo = self._joint_payment_repo
        if not plans or joint_repo is None:
            return

        incomes_by_expense = self._joint_incomes_by_expense(joint_repo)
        for plan in plans:
            self._delete_contribution_pairs(plan, incomes_by_expense, joint_repo)
            for row in plan.due:
                self._book_contribution(plan.sub, row, joint_repo)
            self._repair_contribution(plan, incomes_by_expense, joint_repo)

    @staticmethod
    def _joint_incomes_by_expense(
        joint_repo: "PaymentRepository",
    ) -> dict[str, entities.IncomePaymentModel]:
        """Return the subscription-generated joint incomes, keyed by their expense.

        An income leg carries ``subscription_id`` too, but it lives in the joint
        slice the personal repository cannot see, so it is never mistaken for the
        expense leg's "already done" marker.
        """
        return {
            str(payment.linked_payment_id): payment
            for payment in joint_repo.get_all()
            if isinstance(payment, entities.IncomePaymentModel)
            and payment.subscription_id is not None
            and payment.linked_payment_id is not None
        }

    def _delete_contribution_pairs(
        self,
        plan: _ContributionPlan,
        incomes_by_expense: dict[str, entities.IncomePaymentModel],
        joint_repo: "PaymentRepository",
    ) -> None:
        """Delete both legs of every payment this subscription supersedes."""
        if not plan.superseded:
            return
        income_ids = [
            str(income.id)
            for expense_id in sorted(plan.superseded)
            if (income := incomes_by_expense.get(expense_id)) is not None
        ]
        joint_repo.apply_deletions(income_ids)
        self._payment_repo.apply_deletions(sorted(plan.superseded))

    def _book_contribution(
        self,
        sub: entities.SubscriptionModel,
        row: entities.RawRow,
        joint_repo: "PaymentRepository",
    ) -> None:
        """Book a due contribution as a cross-linked pair of payments."""
        expense = _as_expense(self._payment_repo.build_entities([row])[0])
        income = self._build_income_leg(sub, expense, joint_repo)
        linked_payments.write_linked_pair(
            self._payment_repo,
            joint_repo,
            expense,
            income,
        )

    def _repair_contribution(
        self,
        plan: _ContributionPlan,
        incomes_by_expense: dict[str, entities.IncomePaymentModel],
        joint_repo: "PaymentRepository",
    ) -> None:
        """Finish any pair whose expense landed but whose income did not.

        Without this a partial write is permanent: the next run sees a future
        expense for the subscription, treats it as already booked, and the joint
        leg is never written. Each surviving future expense is checked against
        the incomes actually in the joint books, so a pair that is merely missing
        its forward link is linked rather than written again.
        """
        for expense in plan.current_payments:
            if expense.payment_date < self._today or str(expense.id) in plan.superseded:
                continue
            income = incomes_by_expense.get(str(expense.id))
            if income is None:
                income = self._build_income_leg(plan.sub, expense, joint_repo)
                linked_payments.complete_linked_pair(
                    self._payment_repo,
                    joint_repo,
                    expense,
                    income,
                )
            else:
                linked_payments.link_expense_forward(
                    self._payment_repo,
                    expense,
                    income.id,
                )

    @staticmethod
    def _build_income_leg(
        sub: entities.SubscriptionModel,
        expense: entities.ExpensePaymentModel,
        joint_repo: "PaymentRepository",
    ) -> entities.IncomePaymentModel:
        """Build the joint income mirroring an expense leg.

        Through the joint repository's gate, so the row leaves with the joint
        ownership and account id that repository writes under — the account is
        never threaded through this use case.
        """
        row: entities.RawRow = {
            "payment_type": "income",
            "name": expense.name,
            "income": expense.expense,
            "payment_date": expense.payment_date,
            "bank_account_id": sub.joint_bank_account_id,
            "income_source_id": sub.joint_income_source_id,
            "subscription_id": sub.id,
            "linked_payment_id": expense.id,
        }
        return _as_income(joint_repo.build_entities([row])[0])

    def _reconcile_subscription(
        self,
        sub: entities.SubscriptionModel,
        current_payments: list[entities.ExpensePaymentModel],
    ) -> tuple[list[entities.RawRow], list[str]]:
        """Return what this subscription needs written and removed.

        Args:
            sub: The subscription to reconcile.
            current_payments: Its existing subscription-generated payments.

        Returns:
            The raw rows for any payment now due — at most one — and the ids of
            any payments it supersedes.

        """
        deleted_ids: list[str] = []
        future_payments = [
            payment
            for payment in current_payments
            if payment.payment_date >= self._today
        ]

        is_expired = sub.end_date is not None and sub.end_date < self._today
        if not sub.is_active or is_expired:
            deleted_ids.extend(str(payment.id) for payment in future_payments)
            return [], deleted_ids

        if sub.end_date:
            expired = [
                payment
                for payment in future_payments
                if payment.payment_date > sub.end_date
            ]
            deleted_ids.extend(str(payment.id) for payment in expired)
            future_payments = [
                payment
                for payment in future_payments
                if payment.payment_date <= sub.end_date
            ]

        if future_payments:
            return [], deleted_ids

        next_date = self._compute_next_date(sub)
        if next_date is None:
            return [], deleted_ids

        due: list[entities.RawRow] = [
            {
                "payment_type": "expense",
                "name": f"Sub: {sub.name}",
                "expense": sub.amount,
                "payment_date": next_date,
                "bank_account_id": sub.bank_account_id,
                "expense_source_id": sub.expense_source_id,
                "subscription_id": sub.id,
            },
        ]
        return due, deleted_ids

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
