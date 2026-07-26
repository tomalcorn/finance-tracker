"""Use case for logging the expense a quick-entry button stands for."""

import datetime
import uuid
from typing import TYPE_CHECKING, Annotated

import pydantic

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    from ports import repository


def _today() -> datetime.date:
    """Return the current UTC date.

    Read per call rather than fixed at import: the app process outlives a day,
    and a stale date would file every later tap under the wrong day.
    """
    return datetime.datetime.now(tz=datetime.UTC).date()


class QuickPaymentDetails(pydantic.BaseModel):
    """What a tap supplies on top of the button's preset.

    Every field is optional and each one set wins over the preset — a ``PROMPT``
    button's form fills in what the button deliberately left blank, and may
    correct what it did not. A field left ``None`` means "not supplied", so the
    preset stands; it is not a way to clear a preset value.
    """

    model_config = pydantic.ConfigDict(frozen=True)

    name: Annotated[
        str | None,
        pydantic.Field(description="The name to log the payment under."),
    ] = None
    expense: Annotated[
        float | None,
        pydantic.Field(description="The expense amount.", gt=0),
    ] = None
    bank_account_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The bank account the money leaves."),
    ] = None
    expense_source_id: Annotated[
        uuid.UUID | None,
        pydantic.Field(description="The expense source to book against."),
    ] = None
    payment_date: Annotated[
        datetime.date | None,
        pydantic.Field(description="The date to file the payment under."),
    ] = None


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
        button_id: uuid.UUID,
        details: QuickPaymentDetails | None = None,
    ) -> entities.ExpensePaymentModel:
        """Log the payment the given button stands for.

        Args:
            button_id: The button that was tapped.
            details: What the tap supplied on top of the preset. A ``LOG``
                button needs none; a ``PROMPT`` button's form passes what the
                user filled in.

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
        supplied = details or QuickPaymentDetails()

        expense = supplied.expense if supplied.expense is not None else button.expense
        bank_account_id = supplied.bank_account_id or button.bank_account_id
        self._check_complete(button, expense, bank_account_id)

        row: entities.RawRow = {
            "name": supplied.name or button.name,
            "expense": expense,
            "payment_date": (supplied.payment_date or _today()).isoformat(),
            "checked": False,
            "bank_account_id": str(bank_account_id),
            "expense_source_id": _optional_id(
                supplied.expense_source_id or button.expense_source_id,
            ),
            "payment_type": "expense",
        }
        return self._write(row, button)

    @staticmethod
    def _check_complete(
        button: entities.QuickButtonModel,
        expense: float | None,
        bank_account_id: uuid.UUID | None,
    ) -> None:
        """Reject a tap that cannot produce a whole payment.

        A ``LOG`` button holds these already (the entity refuses to exist
        otherwise), so in practice this catches a ``PROMPT`` button tapped
        without the fields its form was there to collect.

        Raises:
            IncompleteQuickPaymentError: Either field is still missing.

        """
        missing = [
            field
            for field, value in (
                ("an amount", expense),
                ("a bank account", bank_account_id),
            )
            if value is None
        ]
        if missing:
            raise errors.IncompleteQuickPaymentError(button.name, missing)

    def _resolve_button(self, button_id: uuid.UUID) -> entities.QuickButtonModel:
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


def _optional_id(value: uuid.UUID | None) -> str | None:
    """Return an id as a raw-row string, passing None straight through."""
    return str(value) if value is not None else None
