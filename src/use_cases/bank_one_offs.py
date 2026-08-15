"""Use-case with the steps to complete after a user fills in the Bank It! dialog."""

from typing import TYPE_CHECKING

from domain import entities
from use_cases import errors

if TYPE_CHECKING:
    import datetime
    import uuid

    from ports import repository


class BankOneOffsUseCase:
    """Use-case for handling the Bank It! action."""

    def __init__(
        self,
        one_off_repo: "repository.Repository[entities.OneOffItemModel]",
        budget_tracker_repo: "repository.Repository[entities.BudgetTrackerItemModel]",
        expense_source_repo: "repository.Repository[entities.ExpenseSourceModel]",
        payment_repo: "repository.Repository[entities.AnyPaymentModel]",
    ) -> None:
        """Construct BankOneOffsUseCase."""
        self._one_off_repo = one_off_repo
        self._budget_tracker_repo = budget_tracker_repo
        self._expense_source_repo = expense_source_repo
        self._payment_repo = payment_repo

    def _resolve_one_offs_expense_source(self) -> "uuid.UUID | None":
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
        item_ids: list["uuid.UUID"],
        bank_account_id: "uuid.UUID",
        payment_date: "datetime.date",
    ) -> None:
        """Execute the BankOneOffsUseCase.

        Raises:
            AmountToBankLTEZeroError: when the item requested to be banked has an amount
                to bank thats less than or equal to zero.

        """
        items = self._one_off_repo.get_by_ids(item_ids)

        for item in items:
            if item.current_month <= 0:
                raise errors.AmountToBankLTEZeroError(item.name)

        category_id = self._resolve_one_offs_expense_source()

        banked_items = []
        payment_rows: list[entities.RawRow] = []
        for item in items:
            monthly_contribution = item.current_month
            # Entities are frozen: banking produces a new item rather than
            # mutating the stored one in place.
            banked_items.append(
                entities.OneOffItemModel.model_validate(
                    item.model_copy(
                        update={
                            "banked": item.banked + monthly_contribution,
                            "current_month": 0,
                        },
                    ),
                ),
            )
            payment_rows.append(
                {
                    "payment_type": "expense",
                    "name": f"Bank: {item.name}",
                    "expense": monthly_contribution,
                    "payment_date": payment_date,
                    "bank_account_id": bank_account_id,
                    "category_id": category_id,
                },
            )

        self._one_off_repo.save_entities(banked_items)
        self._payment_repo.save_entities(
            self._payment_repo.build_entities(payment_rows),
        )
