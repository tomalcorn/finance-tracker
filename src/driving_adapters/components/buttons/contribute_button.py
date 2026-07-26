"""Module for the ContributeButton class."""

import datetime
import logging
import uuid

import streamlit as st

from driving_adapters import lookups
from driving_adapters.components.buttons import constants
from use_cases import contribute_to_joint, errors

logger = logging.getLogger(__name__)


def _can_submit(
    amount: float | None,
    from_account_id: str | None,
    to_account_id: str | None,
    income_source_id: str | None,
) -> bool:
    """Return whether the contribution form is complete enough to submit.

    A submittable contribution needs a positive amount, a personal source
    account, a joint destination account, and the joint income source the
    arriving money is booked against. An empty dropdown (no joint bank account
    or no joint income source exists) leaves its id ``None``, so this also
    enforces the "needs one of those first" guards.
    """
    return (
        amount is not None
        and amount > 0
        and from_account_id is not None
        and to_account_id is not None
        and income_source_id is not None
    )


class ContributeButton:
    """Button that records a contribution from a personal account to the joint one.

    Mirrors ``BankButton``: a button opens a dialog that drives a single use
    case (``ContributeToJointUseCase``). The use case resolves the hidden
    "Joint" expense source and the user's joint account itself, so the dialog
    only collects the amount, the personal source account, the joint
    destination account, the joint income source, and the date.
    """

    def __init__(
        self,
        contribute_use_case: contribute_to_joint.ContributeToJointUseCase,
        personal_bank_account_map: dict[str, str],
        joint_bank_account_map: dict[str, str],
        joint_income_source_map: dict[str, str],
    ) -> None:
        """Initialize the ContributeButton instance.

        Args:
            contribute_use_case: The contribution use case to drive on submit.
            personal_bank_account_map: ``{id: name}`` of the user's personal
                bank accounts — the source the money leaves.
            joint_bank_account_map: ``{id: name}`` of the joint account's bank
                accounts — the destination the money arrives in.
            joint_income_source_map: ``{id: name}`` of the joint account's
                income sources — what the arriving money is booked against.

        """
        self._contribute_use_case = contribute_use_case
        self._personal_bank_account_map = personal_bank_account_map
        self._joint_bank_account_map = joint_bank_account_map
        self._joint_income_source_map = joint_income_source_map

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

        if not self._joint_income_source_map:
            st.warning(
                "You need a joint income source to contribute against, so the "
                "money shows up in the joint budget. Add one on the joint "
                "budget tracker first, then come back to make a contribution.",
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
        income_source = st.selectbox(
            "Income source (joint)",
            options=list(self._joint_income_source_map.keys()),
            format_func=lookups.make_name_formatter(self._joint_income_source_map),
            key="contribute_income_source",
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

        submitted = st.button(
            "Contribute",
            disabled=not _can_submit(amount, from_account, to_account, income_source),
            key="contribute_submit",
        )
        # The four re-checks narrow the widget outputs to non-None for the
        # type checker; ``disabled`` already makes the button unclickable
        # unless _can_submit held, so this branch only runs when they are set.
        if (
            submitted
            and amount is not None
            and from_account
            and to_account
            and income_source
        ):
            try:
                self._contribute_use_case.execute(
                    amount=float(amount),
                    from_bank_account_id=uuid.UUID(from_account),
                    to_bank_account_id=uuid.UUID(to_account),
                    income_source_id=uuid.UUID(income_source),
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
