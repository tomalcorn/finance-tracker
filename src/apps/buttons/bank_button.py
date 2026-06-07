"""Module for the BankButton class."""

import datetime
import uuid

import streamlit as st

from domain import entities
from libs import auth, data_client
from libs.buttons import constants
from libs.dfes import constants as dfe_constants


class BankButton:
    """Button that banks current month savings for one-off items."""

    def __init__(
        self,
        one_offs_table: str,
        tables_to_clear: list[dfe_constants.TableNames],
    ) -> None:
        """Initialize the BankButton instance."""
        self._one_offs_table = one_offs_table
        self._tables_to_clear = tables_to_clear

    @staticmethod
    def _get_expense_source_id() -> str | None:
        """Find the expense source linked to the one-offs budget tracker item."""
        budget_tracker_data = data_client.get_data(
            table_name="budget_tracker",
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
            table_name="expense_sources",
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

    def _bank_items(
        self,
        items: list[dict],
        bank_account_id: str,
        expense_source_id: str | None,
    ) -> None:
        """Perform the banking operation for the selected one-off items."""
        for item in items:
            amount = float(item["current_month"])
            if amount <= 0:
                continue

            new_banked = float(item.get("banked", 0)) + amount
            data_client.update_backend(
                table_name=self._one_offs_table,
                updates=entities.BackendUpdates(
                    edited_rows={
                        str(item["id"]): {
                            "banked": new_banked,
                            "current_month": 0,
                        },
                    },
                ),
                tables_to_clear=self._tables_to_clear,
            )

            payment = entities.ExpensePaymentModel(
                user_id=auth.get_current_user(),
                name=f"Bank: {item['name']}",
                expense=amount,
                payment_date=datetime.datetime.now(tz=datetime.UTC).date(),
                bank_account_id=uuid.UUID(bank_account_id),
                expense_source_id=(
                    uuid.UUID(expense_source_id) if expense_source_id else None
                ),
                payment_type="expense",
            )
            data_client.update_backend(
                table_name=dfe_constants.TableNames.PAYMENTS.value,
                updates=entities.BackendUpdates(
                    added_rows=[payment.model_dump(mode="json", exclude_none=True)],
                ),
                tables_to_clear=self._tables_to_clear,
            )

    @st.dialog("Bank It")
    def _bank_it_dialog(
        self,
        bankable_items: list[dict],
        bank_account_map: dict[str, str],
        expense_source_id: str | None,
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
            format_func=lambda x: bank_account_map.get(x, "Unknown"),
            key="bank_it_bank_account",
        )

        if selected_ids:
            total = sum(
                float(item_options[sid]["current_month"]) for sid in selected_ids
            )
            st.markdown(f"**Total to bank: £{total:,.2f}**")

        can_submit = bool(selected_ids) and selected_bank_account is not None
        if st.button("Bank It", disabled=not can_submit, key="bank_it_submit"):
            selected_items = [item_options[sid] for sid in selected_ids]
            self._bank_items(
                selected_items,
                str(selected_bank_account),
                expense_source_id,
            )
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
            bank_accounts_data = data_client.get_data(
                table_name="bank_accounts",
                query_string="*",
            )
            bank_account_map = {
                str(ba["id"]): str(ba["name"]) for ba in bank_accounts_data
            }
            expense_source_id = self._get_expense_source_id()
            self._bank_it_dialog(bankable_items, bank_account_map, expense_source_id)
