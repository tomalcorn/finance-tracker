"""Module for the ContributeButton class."""

import datetime
import logging
import uuid

import streamlit as st

from driving_adapters import lookups
from driving_adapters.components.buttons import constants
from use_cases import contribute_to_joint, errors

logger = logging.getLogger(__name__)


def _validated_submission(
    amount: float | None,
    from_account_id: str | None,
    to_account_id: str | None,
) -> tuple[float, str, str] | None:
    """Return the validated ``(amount, source, destination)``, or None if incomplete.

    A submittable contribution needs a positive amount, a personal source
    account, and a joint destination account. An empty destination dropdown
    (no joint bank account exists) leaves ``to_account_id`` ``None``, so this
    also enforces the "needs a joint bank account first" guard. Returning the
    narrowed triple lets the caller compute it once and reuse it for both the
    button's disabled state and the submit branch.
    """
    if amount is not None and amount > 0 and from_account_id and to_account_id:
        return amount, from_account_id, to_account_id
    return None


class ContributeButton:
    """Button that records a contribution from a personal account to the joint one.

    Mirrors ``BankButton``: a button opens a dialog that drives a single use
    case (``ContributeToJointUseCase``). The use case resolves the hidden
    "Joint" expense source and the user's joint account itself, so the dialog
    only collects the amount, the personal source account, the joint
    destination account, and the date.
    """

    def __init__(
        self,
        contribute_use_case: contribute_to_joint.ContributeToJointUseCase,
        personal_bank_account_map: dict[str, str],
        joint_bank_account_map: dict[str, str],
    ) -> None:
        """Initialize the ContributeButton instance.

        Args:
            contribute_use_case: The contribution use case to drive on submit.
            personal_bank_account_map: ``{id: name}`` of the user's personal
                bank accounts — the source the money leaves.
            joint_bank_account_map: ``{id: name}`` of the joint account's bank
                accounts — the destination the money arrives in.

        """
        self._contribute_use_case = contribute_use_case
        self._personal_bank_account_map = personal_bank_account_map
        self._joint_bank_account_map = joint_bank_account_map

    @staticmethod
    def _get_today_date() -> datetime.date:
        return datetime.datetime.now(tz=datetime.UTC).date()

    @st.dialog("Contribute")
    def _contribute_dialog(self) -> None:
        """Render the contribution dialog."""
        if not self._joint_bank_account_map:
            st.warning(
                "You need a joint bank account to contribute to. Add one on the "
                "joint account first, then come back to make a contribution.",
            )
            return

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            value=None,
            format="%.2f",
            key="contribute_amount",
        )
        from_account = st.selectbox(
            "From (personal account)",
            options=list(self._personal_bank_account_map.keys()),
            format_func=lookups.make_name_formatter(self._personal_bank_account_map),
            key="contribute_from_account",
        )
        to_account = st.selectbox(
            "To (joint account)",
            options=list(self._joint_bank_account_map.keys()),
            format_func=lookups.make_name_formatter(self._joint_bank_account_map),
            key="contribute_to_account",
        )
        selected_date = st.date_input(
            "Date",
            value=self._get_today_date(),
            key="contribute_date",
        )
        payment_date = (
            selected_date
            if isinstance(selected_date, datetime.date)
            else self._get_today_date()
        )

        # Computed once: it both gates the button and, being the narrowed
        # triple, carries the values the submit branch needs without re-checking.
        submission = _validated_submission(amount, from_account, to_account)
        submitted = st.button(
            "Contribute",
            disabled=submission is None,
            key="contribute_submit",
        )
        if submitted and submission is not None:
            contribution_amount, from_account_id, to_account_id = submission
            try:
                self._contribute_use_case.execute(
                    amount=contribution_amount,
                    from_bank_account_id=uuid.UUID(from_account_id),
                    to_bank_account_id=uuid.UUID(to_account_id),
                    payment_date=payment_date,
                )
            except errors.ContributionError:
                st.error(
                    "Could not record the contribution. Please contact support.",
                )
                logger.exception("Contribution failed.")
                st.stop()
            st.rerun()

    def __call__(self) -> None:
        """Render the Contribute button, opening the dialog when clicked."""
        if st.button(
            label="Contribute to Joint",
            icon=constants.ButtonIcons.CONTRIBUTE,
            key="contribute_button",
        ):
            self._contribute_dialog()
