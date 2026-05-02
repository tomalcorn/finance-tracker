"""Bank accounts block for the finance tracker app."""

import pandas as pd
import streamlit as st

from libs import data_client
from libs.buttons import constants
from libs.dfes import base_dfe
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


def _build_dfe() -> base_dfe.DFE:
    """Build the DFE for the bank accounts block."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
                read_table=_VIEW_NAME,
            ),
            backend_model=backend_models.BankAccountModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        required=True,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="starting_balance",
                    column_config=st.column_config.NumberColumn(
                        "Starting Balance",
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
                        "Current Balance",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Balance",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_SAMPLE_DATA,
            tables_to_clear=_TABLES_TO_CLEAR,
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
        key_prefix=_TABLE_NAME,
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
    metrics_tab, table_tab = st.tabs(
        [constants.TabIcons.OVERVIEW, constants.TabIcons.TABLE],
    )

    with metrics_tab:
        _render_metrics_tab()

    with table_tab:
        dfe = _build_dfe()
        dfe.load_input_data()
        dfe.render()
