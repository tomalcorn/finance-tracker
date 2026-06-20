"""Use-case with the steps to complete after a user fills in the Bank It! dialog."""

import datetime
import uuid

from domain import entities
from ports import repository
from ui import data_client
from ui.components.dfes import constants as dfe_constants
from use_cases import errors

_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.BUDGET_TRACKER_VIEW,
]


def _get_expense_source_id() -> str | None:
    """Find the expense source linked to the one-offs budget tracker item."""
    budget_tracker_data = data_client.get_data(
        table_name=dfe_constants.TableNames.BUDGET_TRACKER.value,
        query_string="id,name",
    )
    one_offs_bt_id = next(
        (
            str(bt["id"])
            for bt in budget_tracker_data
            if bt.get("name") == entities.BudgetTrackerName.ONE_OFFS
        ),
        None,
    )
    if one_offs_bt_id is None:
        return None

    expense_sources = data_client.get_data(
        table_name=dfe_constants.TableNames.EXPENSE_SOURCES.value,
        query_string="id,name,budget_tracker_ids",
    )

    def _get_bt_ids(es: data_client.JsonDict) -> list:
        bt_ids = es.get("budget_tracker_ids")
        return bt_ids if isinstance(bt_ids, list) else []

    return next(
        (
            str(es["id"])
            for es in expense_sources
            if one_offs_bt_id in [str(x) for x in _get_bt_ids(es)]
        ),
        None,
    )


class BankOneOffsUseCase:
    """Use-case for handling the Bank It! action."""

    def __init__(
        self,
        one_off_repo: repository.OneOffRepository,
        budget_tracker_repo: repository.BudgetTrackerRepository,
        expense_source_repo: repository.ExpenseSourceRepository,
        payment_repo: repository.PaymentRepository,
    ) -> None:
        """Construct HandleBankItUseCase."""
        self._one_off_repo = one_off_repo
        self._budget_tracker_repo = budget_tracker_repo
        self._expense_source_repo = expense_source_repo
        self._payment_repo = payment_repo

    def _resolve_one_offs_expense_source(self) -> uuid.UUID | None:
        budget_trackers = self._budget_tracker_repo.get_all()
        one_offs_tracker = next(
            (
                budget_tracker
                for budget_tracker in budget_trackers
                if budget_tracker.name == entities.BudgetTrackerName.ONE_OFFS
            ),
            None,
        )
        if one_offs_tracker is None:
            return None

        expense_sources = self._expense_source_repo.get_all()
        match = next(
            (
                expense_source
                for expense_source in expense_sources
                if one_offs_tracker.id in (expense_source.budget_tracker_ids or [])
            ),
            None,
        )
        return match.id if match else None

    def execute(
        self,
        item_ids: list[uuid.UUID],
        bank_account_id: uuid.UUID,
        payment_date: datetime.date,
    ) -> None:
        """Execute the HandleBankItUseCase.

        Raises:
            AmountToBankLTEZeroError: when the item requested to be banked has an amount
                to bank thats less than or equal to zero.

        """
        items = self._one_off_repo.get_by_ids(item_ids)

        expense_source_id = self._resolve_one_offs_expense_source()

        for item in items:
            if item.current_month <= 0:
                raise errors.AmountToBankLTEZeroError(item.name)

            monthly_contribution = item.current_month
            item.banked += monthly_contribution
            item.current_month = 0
            self._one_off_repo.save(item)

            payment = entities.ExpensePaymentModel(
                user_id=item.user_id,
                name=f"Bank: {item.name}",
                expense=monthly_contribution,
                payment_date=payment_date,
                bank_account_id=bank_account_id,
                expense_source_id=expense_source_id,
            )
            self._payment_repo.save(payment)
