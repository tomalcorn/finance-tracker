"""Use case for logging the expense a quick-entry button stands for."""

import datetime
from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    import uuid

    from ports import repository


def _today() -> datetime.date:
    """Return the current UTC date.

    Read per call rather than fixed at import: the app process outlives a day,
    and a stale date would file every later tap under the wrong day.
    """
    return datetime.datetime.now(tz=datetime.UTC).date()


class LogQuickPaymentUseCase:
    """Turns one tap of a quick-entry button into an expense payment.

    The caller passes only the button's id: the preset it holds (name, amount,
    bank account, expense source) is read back through the repository, so the UI
    never has to know which payment fields a tap fills in. The button is read
    from the same cache entry the page rendered from, so the read costs no extra
    fetch.

    Both repositories are built in the same ownership mode, so tapping a joint
    button books the payment into the joint ledger and a personal one into the
    user's own.
    """

    def __init__(
        self,
        quick_button_repo: "repository.Repository[entities.QuickButtonModel]",
        payment_repo: "repository.Repository[entities.AnyPaymentModel]",
    ) -> None:
        """Construct LogQuickPaymentUseCase.

        Args:
            quick_button_repo: The quick buttons available in this mode.
            payment_repo: Payments repository in the same mode.

        """
        self._quick_button_repo = quick_button_repo
        self._payment_repo = payment_repo

    def execute(
        self,
        button_id: "uuid.UUID",
        payment_date: datetime.date | None = None,
    ) -> entities.ExpensePaymentModel:
        """Log the payment the given button stands for.

        Args:
            button_id: The button that was tapped.
            payment_date: The date to file the payment under. Defaults to today.

        Returns:
            The payment that was written, so a caller can confirm what it logged.

        Raises:
            QuickButtonNotFoundError: The button no longer exists — it was
                removed (or is another owner's) since the page was rendered.
            QuickPaymentWriteError: The button could not be read, or the payment
                could not be written.

        """
        button = self._resolve_button(button_id)
        row: entities.RawRow = {
            "name": button.name,
            "expense": button.expense,
            "payment_date": (payment_date or _today()).isoformat(),
            "checked": False,
            "bank_account_id": str(button.bank_account_id),
            "expense_source_id": (
                str(button.expense_source_id)
                if button.expense_source_id is not None
                else None
            ),
            "payment_type": "expense",
        }
        return self._write(row, button)

    def _resolve_button(self, button_id: "uuid.UUID") -> entities.QuickButtonModel:
        """Return the button that was tapped.

        Raises:
            QuickButtonNotFoundError: No such button in this ownership mode.
            QuickPaymentWriteError: The button could not be read.

        """
        try:
            buttons = self._quick_button_repo.get_by_ids([button_id])
        except port_errors.RepositoryError as e:
            msg = f"Failed to read quick button {button_id}: {e}"
            raise errors.QuickPaymentWriteError(msg) from e

        if not buttons:
            raise errors.QuickButtonNotFoundError(str(button_id))
        return buttons[0]

    def _write(
        self,
        row: entities.RawRow,
        button: entities.QuickButtonModel,
    ) -> entities.ExpensePaymentModel:
        """Build the raw row into a payment through the gate, then persist it.

        Raises:
            QuickPaymentWriteError: The row is not a valid payment, or the write
                failed.

        """
        try:
            payments = self._payment_repo.build_entities([row])
            self._payment_repo.save_entities(payments)
        except port_errors.RepositoryError as e:
            msg = (
                f"Failed to log {button.expense} for quick button "
                f"{button.name!r} ({button.id}): {e}"
            )
            raise errors.QuickPaymentWriteError(msg) from e

        # The gate parses the discriminated union, and payment_type pins the
        # branch to the expense one.
        payment = payments[0]
        if not isinstance(payment, entities.ExpensePaymentModel):  # pragma: no cover
            msg = f"Quick button {button.id} produced a {type(payment).__name__}."
            raise errors.QuickPaymentWriteError(msg)
        return payment
