"""Payments block for the finance tracker app."""

import datetime
import typing
from collections.abc import Callable

import pandas as pd
import streamlit as st

from apps import data_client
from apps.buttons import add_button, filter_button
from libs.buttons import constants
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models


class PaymentsBlock:
    """Block for displaying and editing payments."""

    _TABLE_NAME = "payments"
    _TABLES_TO_CLEAR: typing.ClassVar[list[dfe_constants.TableNames]] = [
        dfe_constants.TableNames.PAYMENTS,
        dfe_constants.TableNames.BANK_ACCOUNTS,
        dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    ]

    def __init__(self) -> None:
        """Initialize the PaymentsBlock."""
        self._add_button = add_button.AddButton(
            table_name=self._TABLE_NAME,
            backend_model=backend_models.PaymentsModel,
        )
        self._filter_button = filter_button.FilterButton(table_name=self._TABLE_NAME)

        self._sample_data = pd.DataFrame(
            {
                "name": ["Example Data"],
                "expense": [0],
                "payment_date": ["2025-06-01"],
                "checked": [False],
                "created_at": ["2025-06-01"],
                "bank_account_id": ["example bank account"],
                "expense_source_id": ["example expense source"],
            },
        )

    def _build_configs(
        self,
        bank_account_ids: list[str],
        get_bank_account_name: Callable[[str | float], str],
        expense_source_ids: list[str],
        get_expense_source_name: Callable[[str | float], str],
    ) -> list[frontend_models.DFEColumnConfig]:
        """Build column configs using current bank account and expense source data."""
        return [
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config=st.column_config.TextColumn(
                    "🔠 Name",
                    required=True,
                ),
                button_label="Name",
                input_widget=st.text_input,
                input_kwargs={"value": None},
            ),
            frontend_models.DFEColumnConfig(
                column_name="payment_date",
                column_config=st.column_config.DateColumn(
                    "📆 Date",
                    format="localized",
                ),
                button_label="Payment Date",
                input_widget=st.date_input,
                sorting=constants.SortingValues.DESC,
                filters=frontend_models.Filters(
                    gte=datetime.date(2026, 1, 1),
                    lte=datetime.date(2026, 12, 31),
                ),
            ),
            frontend_models.DFEColumnConfig(
                column_name="expense",
                column_config=st.column_config.NumberColumn(
                    "💵 Expense",
                    format="£%.2f",
                ),
                button_label="Expense",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            frontend_models.DFEColumnConfig(
                column_name="checked",
                column_config=st.column_config.CheckboxColumn(
                    "✅ Checked",
                ),
                button_label="Checked",
                input_widget=st.checkbox,
                input_kwargs={"value": False},
            ),
            frontend_models.DFEColumnConfig(
                column_name="bank_account_id",
                column_config=st.column_config.SelectboxColumn(
                    "Bank Account",
                    help="Select a bank account",
                    options=bank_account_ids,
                    format_func=get_bank_account_name,
                ),
                button_label="Bank Account",
                input_widget=st.selectbox,
                input_kwargs={
                    "options": bank_account_ids,
                    "index": None,
                    "format_func": get_bank_account_name,
                },
                format_func=get_bank_account_name,
            ),
            frontend_models.DFEColumnConfig(
                column_name="expense_source_id",
                column_config=st.column_config.SelectboxColumn(
                    "Expense Source",
                    help="Select an expense source",
                    options=expense_source_ids,
                    format_func=get_expense_source_name,
                ),
                button_label="Expense Source",
                input_widget=st.selectbox,
                input_kwargs={
                    "options": expense_source_ids,
                    "index": None,
                    "format_func": get_expense_source_name,
                },
                format_func=get_expense_source_name,
            ),
        ]

    def commit(self) -> None:
        """Apply any pending backend updates for this block."""
        data_client.commit(
            table_name=self._TABLE_NAME,
            tables_to_clear=self._TABLES_TO_CLEAR,
        )

    def render(self) -> None:
        """Render the payments block."""
        bank_accounts_data = data_client.get_data(
            table_name="bank_accounts",
            query_string="*",
        )
        bank_account_map: dict[str, str] = {
            str(ba["id"]): str(ba["name"]) for ba in bank_accounts_data
        }
        bank_account_ids = list(bank_account_map.keys())

        def get_bank_account_name(ba_id: str | float) -> str:
            return bank_account_map.get(str(ba_id), "Unknown Bank Account")

        expense_sources = data_client.get_data(
            table_name="expense_sources",
            query_string="*",
        )
        expense_source_map: dict[str, str] = {
            str(es["id"]): str(es["name"]) for es in expense_sources
        }
        expense_source_ids = list(expense_source_map.keys())

        def get_expense_source_name(es_id: str | float) -> str:
            return expense_source_map.get(str(es_id), "Unknown Expense Source")

        filter_col, _, add_col = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)

        configs = self._build_configs(
            bank_account_ids=bank_account_ids,
            get_bank_account_name=get_bank_account_name,
            expense_source_ids=expense_source_ids,
            get_expense_source_name=get_expense_source_name,
        )

        with add_col:
            new_data_added = self._add_button(col_configs=configs)
        with filter_col:
            # ty can't figure out that configs is a list of DFEColumnConfigBase or
            # DFEColumnConfig, even though it literally is
            filters_changed, configs = self._filter_button(col_configs=configs)  # ty: ignore[invalid-argument-type]

        dfe = base_dfe.DFE(
            table_name=self._TABLE_NAME,
            configs=configs,
        )
        dfe.load_input_data(
            self._sample_data,
            filters_changed=filters_changed,
            new_data_added=new_data_added,
        ).render()
