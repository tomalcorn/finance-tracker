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

    The caller passes the button's id and, for a button that asks before it logs,
    the details its form collected: the preset it holds (name, amount, bank
    account, expense source) is read back through the repository, so the UI never
    has to know which payment fields a tap fills in. The button is read from the
    same cache entry the page rendered from, so the read costs no extra fetch.

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
        overrides: entities.RawRow | None = None,
    ) -> entities.ExpensePaymentModel:
        """Log the payment the given button stands for.

        Args:
            button_id: The button that was tapped.
            overrides: Payment fields the tap supplied, laid over the button's
                preset. A ``LOG`` button passes none; a ``PROMPT`` button's form
                passes what the user filled in. Same shape as any other raw row
                on its way to the gate.

        Returns:
            The payment that was written, so a caller can confirm what it logged.

        Raises:
            QuickButtonNotFoundError: The button no longer exists — it was
                removed (or is another owner's) since the page was rendered.
            IncompleteQuickPaymentError: A field the payment needs is neither
                preset on the button nor supplied by the tap.
            QuickPaymentWriteError: The button could not be read, or the payment
                could not be written.

        """
        button = self._resolve_button(button_id)
        row = {**self._preset_row(button), **dict(overrides or {})}
        self._check_complete(button, row)
        return self._write(row, button)

    @staticmethod
    def _preset_row(button: entities.QuickButtonModel) -> dict[str, object]:
        """Return the payment row the button fills in on its own.

        Complete for a ``LOG`` button, and deliberately full of holes for a
        ``PROMPT`` one — its form supplies the rest.
        """
        return {
            "name": _preset_name(button),
            "expense": button.expense,
            "payment_date": _today().isoformat(),
            "checked": False,
            "bank_account_id": _optional_id(button.bank_account_id),
            "expense_source_id": _optional_id(button.expense_source_id),
            "payment_type": "expense",
        }

    @staticmethod
    def _check_complete(
        button: entities.QuickButtonModel,
        row: dict[str, object],
    ) -> None:
        """Reject a tap that cannot produce a whole payment.

        A ``LOG`` button holds all of this already (the entity refuses to exist
        otherwise, and it falls back to its label for the name), so in practice
        this catches a ``PROMPT`` button tapped without the fields its form was
        there to collect.

        Raises:
            IncompleteQuickPaymentError: A required field is still missing.

        """
        missing: list[str] = []
        if not row["name"]:
            missing.append("a name")
        if row["expense"] is None:
            missing.append("an amount")
        if row["bank_account_id"] is None:
            missing.append("a bank account")

        if missing:
            raise errors.IncompleteQuickPaymentError(button.name, missing)

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
                f"Failed to log a payment for quick button "
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


def _optional_id(value: "uuid.UUID | None") -> str | None:
    """Return an id as a raw-row string, passing None straight through."""
    return str(value) if value is not None else None


def _preset_name(button: entities.QuickButtonModel) -> str:
    """Return the name the button presets for its payment, if it presets one.

    Only a ``LOG`` button falls back to its *label*: it has no form in which to
    be told a name, so borrowing the tile's is the best it can do. A ``PROMPT``
    button that presets none is asking to be given one, and a label like
    "Groceries" is not an answer to that question.
    """
    if button.payment_name:
        return button.payment_name
    if button.mode is entities.QuickButtonMode.LOG:
        return button.name
    return ""
