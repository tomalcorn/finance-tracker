"""Block for the budget tracker section: budget tracker, expense and income sources."""

import pandas as pd
import streamlit as st

from apps.blocks import base_block
from libs import data_client
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_EXPENSE_SOURCES_TABLE = dfe_constants.TableNames.EXPENSE_SOURCES.value
_EXPENSE_SOURCES_VIEW = dfe_constants.TableNames.EXPENSE_SOURCES_VIEW.value


_EXPENSE_SOURCES_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.EXPENSE_SOURCES,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
]


_EXPENSE_SOURCES_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Expense Source"],
        "budget": [0],
        "current_month": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_EXPENSE_SOURCES_TABLE,
        tables_to_clear=_EXPENSE_SOURCES_TABLES_TO_CLEAR,
    )


def render() -> None:
    """Render the budget tracker block."""
    (expense_tab,) = st.tabs(
        ["Expense Sources"],
    )

    with expense_tab:
        base_block.render_dfe_tab(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_EXPENSE_SOURCES_TABLE,
                read_table=_EXPENSE_SOURCES_VIEW,
            ),
            backend_model=backend_models.ExpenseSourceModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn("🔠 Name", required=True),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="budget",
                    column_config=st.column_config.NumberColumn(
                        "💰 Budget",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Budget",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "📐 Split",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                    ),
                    button_label="Split",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "💵 Current Month",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "📊 Progress",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                    ),
                    button_label="Progress",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "💰 Remaining",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_EXPENSE_SOURCES_SAMPLE_DATA,
            tables_to_clear=_EXPENSE_SOURCES_TABLES_TO_CLEAR,
        )
