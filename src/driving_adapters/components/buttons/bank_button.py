"""Module for the BankButton class."""

import datetime
import logging
import uuid

import streamlit as st

from composition import wiring
from driving_adapters import lookups
from driving_adapters.components.buttons import constants
from use_cases import bank_one_offs, errors

logger = logging.getLogger(__name__)


class BankButton:
    """Button that banks current month savings for one-off items."""

    def __init__(
        self,
        bank_one_offs_use_case: bank_one_offs.BankOneOffsUseCase,
    ) -> None:
        """Initialize the BankButton instance."""
        self._bank_one_offs_use_case = bank_one_offs_use_case

    @staticmethod
    def _get_today_date() -> datetime.date:
        return datetime.datetime.now(tz=datetime.UTC).date()

    @st.dialog("Bank It")
    def _bank_it_dialog(
        self,
        bankable_items: list[dict],
        bank_account_map: dict[str, str],
    ) -> None:
        """Render the Bank It dialog."""
        item_options = {str(item["id"]): item for item in bankable_items}
        item_labels = {
            str(item["id"]): f"{item['name']} — £{float(item['current_month']):,.2f}"
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
            total = sum(
                float(item_options[sid]["current_month"]) for sid in selected_ids
            )
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

    def __call__(self, bankable_items: list[dict]) -> None:
        """Render the Bank It button.

        Args:
            bankable_items: List of one-off item dicts with current_month > 0.

        """
        if st.button(
            label="",
            icon=constants.ButtonIcons.BANK,
            key="bank_it_button",
        ):
            bank_account_map = wiring.bank_account_id_name_map()
            self._bank_it_dialog(bankable_items, bank_account_map)
