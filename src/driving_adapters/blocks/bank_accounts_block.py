"""Bank accounts block for the finance tracker app."""

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from driving_adapters.components.buttons import constants
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models
    from driving_adapters.components.dfes import data_source as data_source_mod

_GRID_ID = "bank_accounts"

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Bank Account"],
        "starting_balance": [0],
        "current_balance": [0],
    },
)


def _build_config(
    data_source: "data_source_mod.GridDataSource[read_models.BankAccountView]",
) -> frontend_models.DFEConfig:
    """Build the grid config for the bank accounts block."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id=_GRID_ID,
            data_source=data_source,
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="The name of this account.",
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
                        help="What was in it when you started tracking.",
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
                        help="Starting balance plus every payment since.",
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


def commit(
    data_source: "data_source_mod.GridDataSource[read_models.BankAccountView]",
) -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_build_config(data_source))


def _render_metrics_tab(accounts: "Sequence[read_models.BankAccountView]") -> None:
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
    data_source: "data_source_mod.GridDataSource[read_models.BankAccountView]",
) -> None:
    """Render the bank accounts block.

    Both tabs read the one source. Called after reconciliation, so the computed
    balances the overview shows include the payments it has just written.
    """
    metrics_tab, table_tab = st.tabs(
        [
            f"{constants.TabIcons.OVERVIEW} Overview",
            f"{constants.TabIcons.TABLE} Table",
        ],
    )

    with metrics_tab:
        _render_metrics_tab(data_source.rows())

    with table_tab:
        grid.render(_build_config(data_source))
