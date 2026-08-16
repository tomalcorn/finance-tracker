"""Use-case with the steps to complete after a user fills in the Bank It! dialog."""

from typing import TYPE_CHECKING

from use_cases import errors

if TYPE_CHECKING:
    import datetime
    import uuid

    from domain import entities
    from ports import repository


class BankOneOffsUseCase:
    """Use-case for handling the Bank It! action.

    Banking a pot writes one payment attributed to the pot itself, and nothing
    else. A pot's balance is its opening balance plus the payments booked to it,
    so there is no stored counter to increment; and the planned spend is a plan
    for the month, which nothing decrements.
    """

    def __init__(
        self,
        category_repo: "repository.Repository[entities.CategoryModel]",
        payment_repo: "repository.Repository[entities.AnyPaymentModel]",
    ) -> None:
        """Construct BankOneOffsUseCase."""
        self._category_repo = category_repo
        self._payment_repo = payment_repo

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
        items = self._category_repo.get_by_ids(item_ids)

        for item in items:
            if item.budget <= 0:
                raise errors.AmountToBankLTEZeroError(item.name)

        payment_rows: list[entities.RawRow] = [
            {
                "payment_type": "expense",
                "name": f"Bank: {item.name}",
                "expense": item.budget,
                "payment_date": payment_date,
                "bank_account_id": bank_account_id,
                "category_id": item.id,
            }
            for item in items
        ]

        self._payment_repo.save_entities(
            self._payment_repo.build_entities(payment_rows),
        )
