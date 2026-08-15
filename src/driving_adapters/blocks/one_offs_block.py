"""One-offs block for tracking one-off savings goals."""

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from domain import entities, query, read_models
from driving_adapters.components.buttons import add_button, bank_button, filter_button
from driving_adapters.components.dfes import column_widths, grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from driving_adapters.components.dfes import data_source as data_source_mod
    from use_cases import bank_one_offs

_TABLE_NAME = "one_offs"

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


def _build_config(
    data_source: "data_source_mod.GridDataSource",
    budget_tracker_map: dict[str, str],
) -> frontend_models.DFEConfig:
    """Build the grid config for the one-offs block."""
    one_offs_bt_id = next(
        (
            bt_id
            for bt_id, name in budget_tracker_map.items()
            if name == entities.BudgetTrackerName.ONE_OFFS
        ),
        None,
    )

    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_TABLE_NAME,
            data_source=data_source,
            extra_row_values=(
                {"budget_tracker_id": one_offs_bt_id} if one_offs_bt_id else None
            ),
        ),
        display=frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        help="What you are saving up for.",
                        required=True,
                        width=column_widths.NAME,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="cost",
                    column_config=st.column_config.NumberColumn(
                        "Cost",
                        help="What the item costs in total.",
                        format="£%.2f",
                        required=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Cost",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="current_month",
                    column_config=st.column_config.NumberColumn(
                        "Planned Spend",
                        help="What you intend to put towards it this month.",
                        format="£%.2f",
                        required=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Planned Spend",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="split",
                    column_config=st.column_config.ProgressColumn(
                        "Share of Budget",
                        help="The planned spend as a share of the One-offs budget.",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="blue",
                    ),
                    button_label="Share of Budget",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                    total=True,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="banked",
                    column_config=st.column_config.NumberColumn(
                        "Banked",
                        help="Put aside so far, across every month.",
                        format="£%.2f",
                        required=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Banked",
                    input_widget=st.number_input,
                    input_kwargs={"value": 0.0, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="progress",
                    column_config=st.column_config.ProgressColumn(
                        "% Banked",
                        help="How much of the cost you have banked.",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width=column_widths.PROGRESS,
                        color="blue",
                    ),
                    button_label="% Banked",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.1f"},
                ),
                frontend_models.DFEColumnConfig(
                    editable=False,
                    column_name="remaining",
                    column_config=st.column_config.NumberColumn(
                        "Remaining",
                        help="The amount of the cost still left to bank.",
                        format="£%.2f",
                        disabled=True,
                        width=column_widths.MONEY,
                    ),
                    button_label="Remaining",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                *(
                    [
                        frontend_models.DFEColumnConfig(
                            editable=False,
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
        ),
    )


def commit(
    data_source: "data_source_mod.GridDataSource",
    budget_tracker_map: dict[str, str],
) -> None:
    """Apply any pending backend updates for this block."""
    grid.commit(_build_config(data_source, budget_tracker_map))


def _bankable_items(
    data_source: "data_source_mod.GridDataSource",
) -> list[read_models.OneOffView]:
    """Return the one-offs with an amount pledged for the current month.

    Read through the port rather than off the grid's display frame: banking acts
    on the aggregate, so neither an active column filter nor the sample data an
    empty frame falls back to gets to decide what is bankable.
    """
    return [
        row
        for row in data_source.rows()
        if isinstance(row, read_models.OneOffView) and row.current_month > 0
    ]


def render(
    data_source: "data_source_mod.GridDataSource",
    budget_tracker_map: dict[str, str],
    bank_account_map: dict[str, str],
    bank_one_offs_use_case: "bank_one_offs.BankOneOffsUseCase",
) -> None:
    """Render the one-offs block."""
    config = _build_config(data_source, budget_tracker_map)
    working_df = grid.build_working_df(config)

    add_col, filter_col, bank_col, _ = st.columns([0.05, 0.05, 0.05, 0.85])
    with add_col:
        add_button.render_add_button(config.source, config.display)
    with filter_col:
        filter_button.render_filter_button(config.source, config.display)
    with bank_col:
        bank_btn = bank_button.BankButton(bank_one_offs_use_case, bank_account_map)
        bank_btn(_bankable_items(data_source))

    grid.render_editor(config.display, config.key_prefix, working_df)
