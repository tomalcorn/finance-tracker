"""Module for the BankButton class."""

import datetime
import logging
import typing
import uuid

import streamlit as st

from driving_adapters import lookups
from driving_adapters.components.buttons import constants
from use_cases import bank_one_offs, errors

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models

logger = logging.getLogger(__name__)


class BankButton:
    """Button that banks current month savings for one-off items."""

    def __init__(
        self,
        bank_one_offs_use_case: bank_one_offs.BankOneOffsUseCase,
        bank_account_map: dict[str, str],
    ) -> None:
        """Initialize the BankButton instance."""
        self._bank_one_offs_use_case = bank_one_offs_use_case
        self._bank_account_map = bank_account_map

    @staticmethod
    def _get_today_date() -> datetime.date:
        return datetime.datetime.now(tz=datetime.UTC).date()

    @st.dialog("Bank It")
    def _bank_it_dialog(
        self,
        bankable_items: "Sequence[read_models.CategoryView]",
        bank_account_map: dict[str, str],
    ) -> None:
        """Render the Bank It dialog."""
        if not bankable_items:
            st.warning(
                "Nothing to bank yet. Give a one-off a planned spend first, "
                "then come back to pay it into the pot.",
            )
            return

        if not bank_account_map:
            st.warning(
                "You need a bank account to bank into. Add one below, then come "
                "back to bank your one-offs.",
            )
            return

        item_options = {str(item.id): item for item in bankable_items}
        item_labels = {
            str(item.id): f"{item.name} — £{item.budget:,.2f}"
            for item in bankable_items
        }

        selected_ids = st.multiselect(
            "Select items to bank",
            options=list(item_options.keys()),
            format_func=lambda x: item_labels[x],
            key="bank_it_item_select",
        )

        bank_account_ids = list(bank_account_map.keys())
        selected_bank_account = st.selectbox(
            "Bank Account",
            options=bank_account_ids,
            format_func=lookups.make_name_formatter(bank_account_map),
            key="bank_it_bank_account",
        )

        if selected_ids:
            total = sum(item_options[sid].budget for sid in selected_ids)
            st.markdown(f"**Total to bank: £{total:,.2f}**")

        can_submit = bool(selected_ids) and selected_bank_account is not None
        if st.button("Bank It", disabled=not can_submit, key="bank_it_submit"):
            try:
                self._bank_one_offs_use_case.execute(
                    item_ids=[uuid.UUID(sid) for sid in selected_ids],
                    bank_account_id=uuid.UUID(selected_bank_account),
                    payment_date=self._get_today_date(),
                )
            except errors.BankOneOffsError:
                st.error("Could not bank the requested items. Please contact support.")
                logger.exception("Bank One-Offs failed.")
                st.stop()
            st.rerun()

    def __call__(self, bankable_items: "Sequence[read_models.CategoryView]") -> None:
        """Render the Bank It button, opening the dialog when clicked.

        The button renders whether or not there is anything to bank; an empty
        ``bankable_items`` is explained inside the dialog rather than by the
        button silently disappearing.

        Args:
            bankable_items: The pot views with a ``budget`` (planned spend) > 0.

        """
        if st.button(
            label="",
            icon=constants.ButtonIcons.BANK,
            help="Pay this month's planned spend into the pot.",
            key="bank_it_button",
        ):
            self._bank_it_dialog(bankable_items, self._bank_account_map)
