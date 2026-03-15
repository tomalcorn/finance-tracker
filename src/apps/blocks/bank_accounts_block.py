"""Bank accounts block for the finance tracker app."""

import pandas as pd
import streamlit as st

from apps import data_client
from apps.buttons import add_button, filter_button
from libs.buttons import constants
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models


class BankAccountsBlock:
    """Block for displaying and editing bank accounts."""

    _TABLE_NAME = dfe_constants.TableNames.BANK_ACCOUNTS.value
    _VIEW_NAME = dfe_constants.TableNames.BANK_ACCOUNTS_VIEW.value

    def __init__(self) -> None:
        """Initialize the BankAccountsBlock."""
        self._add_button = add_button.AddButton(
            table_name=self._TABLE_NAME,
            backend_model=backend_models.BankAccountModel,
        )
        self._filter_button = filter_button.FilterButton(table_name=self._TABLE_NAME)

        self._writable_configs: list[frontend_models.DFEColumnConfig] = [
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config=st.column_config.TextColumn("🔠 Name", required=True),
                button_label="Name",
                input_widget=st.text_input,
                input_kwargs={"value": None},
            ),
            frontend_models.DFEColumnConfig(
                column_name="starting_balance",
                column_config=st.column_config.NumberColumn(
                    "💰 Starting Balance",
                    format="£%.2f",
                    required=True,
                ),
                button_label="Starting Balance",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
        ]
        self._readable_config = frontend_models.DFEReadOnlyColumnConfig(
            column_name="current_balance",
            column_config=st.column_config.NumberColumn(
                "💵 Current Balance",
                format="£%.2f",
                disabled=True,
            ),
            button_label="Current Balance",
            input_widget=st.number_input,
            input_kwargs={"value": None, "format": "%.2f"},
        )

        self._sample_data = pd.DataFrame(
            {
                "name": ["Example Bank Account"],
                "starting_balance": [0],
                "current_balance": [0],
            },
        )

    def _render_table_tab(self) -> None:
        """Render the editable table view tab."""
        filter_col, _, add_col = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)

        with add_col:
            new_data_added = self._add_button(col_configs=self._writable_configs)

        configs = [
            *self._writable_configs,
            self._readable_config,
        ]

        with filter_col:
            filters_changed, configs = self._filter_button(col_configs=configs)

        dfe = base_dfe.DFE(
            table_name=self._VIEW_NAME,
            configs=configs,
        )
        dfe.load_input_data(
            self._sample_data,
            filters_changed=filters_changed,
            new_data_added=new_data_added,
        ).render()

        data_client.update_backend(
            table_name=self._TABLE_NAME,
            updates=dfe.backend_updates,
            tables_to_clear=[
                dfe_constants.TableNames.BANK_ACCOUNTS,
                dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
            ],
        )

    def _render_metrics_tab(self) -> None:
        """Render the metrics grid tab showing name and current balance per account."""
        accounts = data_client.get_data(
            table_name=self._VIEW_NAME,
            query_string="name, current_balance",
        )
        cols = st.columns(3)
        for i, account in enumerate(accounts):
            with cols[i % 3]:
                st.metric(
                    label=str(account["name"]),
                    value=f"£{account['current_balance']:,.2f}",
                    border=True,
                )

    def render(self) -> None:
        """Render the bank accounts block."""
        metrics_tab, table_tab = st.tabs(["Overview", "Table"])

        with metrics_tab:
            self._render_metrics_tab()

        with table_tab:
            self._render_table_tab()
