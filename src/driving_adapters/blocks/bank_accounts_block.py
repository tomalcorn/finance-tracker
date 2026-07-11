"""Bank accounts block for the finance tracker app."""

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities
from driving_adapters.components.buttons import constants
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from domain import read_models
    from driving_adapters.components.dfes import data_source as data_source_mod

_TABLE_NAME = "bank_accounts"

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Bank Account"],
        "starting_balance": [0],
        "current_balance": [0],
    },
)


def _build_config(
    data_source: "data_source_mod.GridDataSource",
) -> frontend_models.DFEConfig:
    """Build the grid config for the bank accounts block."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_TABLE_NAME,
            data_source=data_source,
            backend_model=entities.BankAccountModel,
        ),
        display=frontend_models.GridDisplay(
            columns=[
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
                frontend_models.DFEColumnConfig(
                    column_name="current_balance",
                    editable=False,
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


def commit(data_source: "data_source_mod.GridDataSource") -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_build_config(data_source))


def _render_metrics_tab(accounts: "list[read_models.BankAccountView]") -> None:
    """Render the metrics grid tab showing name and current balance per account."""
    cols = st.columns(3)
    for i, account in enumerate(accounts):
        with cols[i % 3]:
            st.metric(
                label=str(account.name),
                value=f"£{account.current_balance:,.2f}",
                border=True,
            )


def render(
    data_source: "data_source_mod.GridDataSource",
    accounts: "list[read_models.BankAccountView]",
) -> None:
    """Render the bank accounts block."""
    metrics_tab, table_tab = st.tabs(
        [
            f"{constants.TabIcons.OVERVIEW} Overview",
            f"{constants.TabIcons.TABLE} Table",
        ],
    )

    with metrics_tab:
        _render_metrics_tab(accounts)

    with table_tab:
        grid.render(_build_config(data_source))
