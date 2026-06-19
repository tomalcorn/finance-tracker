"""One-offs block for tracking one-off savings goals."""

import pandas as pd
import streamlit as st

from apps.buttons import bank_button
from composition import wiring
from domain import entities
from libs import data_client
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import frontend_models

_TABLE_NAME = dfe_constants.TableNames.ONE_OFFS.value
_VIEW_NAME = dfe_constants.TableNames.ONE_OFFS_VIEW.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.BUDGET_TRACKER_VIEW,
]

_BANK_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.BUDGET_TRACKER_VIEW,
]

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example One-Off"],
        "cost": [0],
        "current_month": [0],
        "banked": [0],
        "remaining": [0],
        "progress": [0],
        "split": [0],
    },
)


def _build_dfe() -> base_dfe.DFE:
    """Build the DFE for the one-offs block."""
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

    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
                read_table=_VIEW_NAME,
            ),
            backend_model=entities.OneOffItemModel,
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
                    column_name="cost",
                    column_config=st.column_config.NumberColumn(
                        "Cost",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Cost",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "Current Month",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Current Month",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="banked",
                    column_config=st.column_config.NumberColumn(
                        "Banked",
                        format="£%.2f",
                        required=True,
                    ),
                    button_label="Banked",
                    input_widget=st.number_input,
                    input_kwargs={"value": 0.0, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "Remaining",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "Progress",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                        color="blue",
                    ),
                    button_label="Progress",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "Split",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="small",
                        color="blue",
                    ),
                    button_label="Split",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                *(
                    [
                        frontend_models.DFEReadOnlyColumnConfig(
                            column_name="budget_tracker_id",
                            column_config={"disabled": True},
                            visible=False,
                            filters=frontend_models.Filters(eq=one_offs_bt_id),
                            input_widget=st.text_input,
                        ),
                    ]
                    if one_offs_bt_id
                    else []
                ),
            ],
            sample_data=_SAMPLE_DATA,
            tables_to_clear=_TABLES_TO_CLEAR,
            extra_row_values=(
                {"budget_tracker_id": one_offs_bt_id} if one_offs_bt_id else None
            ),
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
        key_prefix=_TABLE_NAME,
    )


def render() -> None:
    """Render the one-offs block."""
    dfe = _build_dfe()
    dfe.load_input_data()

    # Compose buttons: add, filter, and bank-it in one row
    working_df = dfe.working_df
    bankable_items = []
    if working_df is not None and not working_df.empty:
        bankable_df = working_df[working_df["current_month"] > 0]
        if not bankable_df.empty:
            bankable_items = bankable_df.to_dict("records")

    add_col, filter_col, bank_col, _ = st.columns([0.05, 0.05, 0.05, 0.85])

    with add_col:
        data_added = dfe.add_button(col_configs=dfe.writable_configs)
    with filter_col:
        filters_changed = dfe.filter_button(col_configs=dfe.all_configs)
    with bank_col:
        if bankable_items:
            bank_btn = bank_button.BankButton(wiring.bank_one_offs_use_case())
            bank_btn(bankable_items)

    dfe.refresh(filters_changed=filters_changed, data_added=data_added)
    dfe.render_editor()
