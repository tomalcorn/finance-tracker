"""Base module for blocks."""

import pandas as pd
import streamlit as st

from apps.buttons import add_button, filter_button
from libs import data_client
from libs.buttons import constants
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models


def render_dfe_tab(
    table_names: frontend_models.DFETableNameConfig,
    backend_model: type[backend_models.FinanceTrackerBaseModel],
    configs: list[frontend_models.DFEColumnConfigBase],
    sample_data: pd.DataFrame,
    tables_to_clear: list[dfe_constants.TableNames] | None = None,
) -> None:
    """Render a single DFE tab with add/filter buttons and a dataframe editor."""
    read_table_name = table_names.read_table or table_names.write_table
    write_table_name = table_names.write_table
    key_prefix = table_names.key_prefix or write_table_name

    add_btn = add_button.AddButton(
        table_name=write_table_name,
        key_prefix=key_prefix,
        backend_model=backend_model,
        tables_to_clear=tables_to_clear,
    )
    filter_btn = filter_button.FilterButton(
        table_name=write_table_name,
        key_prefix=key_prefix,
    )

    writable_configs = [
        c
        for c in configs
        if isinstance(c, frontend_models.DFEColumnConfig) and c.visible
    ]

    filter_col, _, add_col = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)
    with add_col:
        new_data_added = add_btn(col_configs=writable_configs)
    with filter_col:
        filters_changed, configs = filter_btn(col_configs=configs)

    if filters_changed:
        data_client.invalidate_table_cache(read_table_name)

    base_dfe.DFE(table_names=table_names, configs=configs).load_input_data(
        sample_data,
        filters_changed=filters_changed,
        new_data_added=new_data_added,
    ).render()
