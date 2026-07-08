"""One-offs block for tracking one-off savings goals."""

import pandas as pd
import streamlit as st

from composition import wiring
from domain import entities, query
from driving_adapters.components.buttons import add_button, bank_button, filter_button
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

_TABLE_NAME = "one_offs"
_VIEW_NAME = "one_offs_view"

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


def _build_config() -> frontend_models.DFEConfig:
    """Build the grid config for the one-offs block."""
    budget_tracker_map = wiring.budget_tracker_id_name_map()
    one_offs_bt_id = next(
        (
            bt_id
            for bt_id, name in budget_tracker_map.items()
            if name == entities.BudgetTrackerName.ONE_OFFS
        ),
        None,
    )

    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(
            write_table=_TABLE_NAME,
            read_table=_VIEW_NAME,
        ),
        data_source=wiring.one_off_data_source(),
        read_via_repository=True,
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
                        filters=query.Filters(eq=one_offs_bt_id),
                        input_widget=st.text_input,
                    ),
                ]
                if one_offs_bt_id
                else []
            ),
        ],
        sample_data=_SAMPLE_DATA,
        extra_row_values=(
            {"budget_tracker_id": one_offs_bt_id} if one_offs_bt_id else None
        ),
    )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_build_config())


def render() -> None:
    """Render the one-offs block."""
    config = _build_config()
    working_df = grid.build_working_df(config)

    bankable_items = []
    if not working_df.empty:
        bankable_df = working_df[working_df["current_month"] > 0]
        if not bankable_df.empty:
            bankable_items = bankable_df.to_dict("records")

    # Compose buttons: add, filter, and bank-it in one row
    add_col, filter_col, bank_col, _ = st.columns([0.05, 0.05, 0.05, 0.85])
    with add_col:
        add_button.render_add_button(config)
    with filter_col:
        filter_button.render_filter_button(config)
    with bank_col:
        if bankable_items:
            bank_btn = bank_button.BankButton(wiring.bank_one_offs_use_case())
            bank_btn(bankable_items)

    grid.render_editor(config, working_df)
