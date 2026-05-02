"""One-offs block for tracking one-off savings goals."""

import pandas as pd
import streamlit as st

from apps.blocks import base_block
from libs import data_client
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_TABLE_NAME = dfe_constants.TableNames.ONE_OFFS.value
_VIEW_NAME = dfe_constants.TableNames.ONE_OFFS_VIEW.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
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


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
    )


def render() -> None:
    """Render the one-offs block."""
    budget_tracker_data = data_client.get_data(
        table_name="budget_tracker",
        query_string="id,name",
    )
    one_offs_bt_id = next(
        (
            str(bt["id"])
            for bt in budget_tracker_data
            if str(bt.get("name", "")).lower() == "one-offs"
        ),
        None,
    )

    base_block.render_dfe_tab(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_TABLE_NAME,
            read_table=_VIEW_NAME,
        ),
        backend_model=backend_models.OneOffItemModel,
        configs=[
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config=st.column_config.TextColumn("🔠 Name", required=True),
                button_label="Name",
                input_widget=st.text_input,
                input_kwargs={"value": None},
            ),
            frontend_models.DFEColumnConfig(
                column_name="cost",
                column_config=st.column_config.NumberColumn(
                    "💰 Cost",
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
                    "💵 Current Month",
                    format="£%.2f",
                    required=True,
                ),
                button_label="Current Month",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
            ),
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="banked",
                column_config=st.column_config.NumberColumn(
                    "🏦 Banked",
                    format="£%.2f",
                    disabled=True,
                ),
                button_label="Banked",
                input_widget=st.number_input,
                input_kwargs={"value": None, "format": "%.2f"},
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
            frontend_models.DFEReadOnlyColumnConfig(
                column_name="progress",
                column_config=st.column_config.ProgressColumn(
                    "📊 Progress",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    color="auto-inverse",
                ),
                button_label="Progress",
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
    )
