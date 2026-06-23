"""Bank accounts block for the finance tracker app."""

import pandas as pd
import streamlit as st

from domain import entities
from ui import data_client
from ui.components.buttons import constants
from ui.components.dfes import base_dfe
from ui.models import frontend_models

_TABLE_NAME = "bank_accounts"
_VIEW_NAME = "bank_accounts_view"

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
            backend_model=entities.BankAccountModel,
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
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
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
        [
            f"{constants.TabIcons.OVERVIEW} Overview",
            f"{constants.TabIcons.TABLE} Table",
        ],
    )

    with metrics_tab:
        _render_metrics_tab()

    with table_tab:
        dfe = _build_dfe()
        dfe.load_input_data()
        data_added, filters_changed = dfe.render_buttons()
        dfe.refresh(filters_changed=filters_changed, data_added=data_added)
        dfe.render_editor()
