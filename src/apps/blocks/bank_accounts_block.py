"""Bank accounts block for the finance tracker app."""

import pandas as pd
import streamlit as st

from apps.blocks import base_block
from libs import data_client
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_TABLE_NAME = dfe_constants.TableNames.BANK_ACCOUNTS.value
_VIEW_NAME = dfe_constants.TableNames.BANK_ACCOUNTS_VIEW.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
]

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Bank Account"],
        "starting_balance": [0],
        "current_balance": [0],
    },
)


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
    )


def _render_metrics_tab() -> None:
    """Render the metrics grid tab showing name and current balance per account."""
    accounts = data_client.get_data(
        table_name=_VIEW_NAME,
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


def render() -> None:
    """Render the bank accounts block."""
    metrics_tab, table_tab = st.tabs(["Overview", "Table"])

    with metrics_tab:
        _render_metrics_tab()

    with table_tab:
        base_block.render_dfe_tab(
            table_name=_TABLE_NAME,
            backend_model=backend_models.BankAccountModel,
            configs=[
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
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="current_balance",
                    column_config=st.column_config.NumberColumn(
                        "💵 Current Balance",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Balance",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_SAMPLE_DATA,
            read_table_name=_VIEW_NAME,
        )
