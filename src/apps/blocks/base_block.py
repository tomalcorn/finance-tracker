"""Base module for blocks."""

from typing import Any

import pandas as pd
import streamlit as st

from apps.buttons import add_button, filter_button
from libs.buttons import constants
from libs.dfes import base_dfe
from libs.models import backend_models, frontend_models


def render_dfe_tab(  # noqa: PLR0913
    table_name: str,
    backend_model: type[backend_models.FinanceTrackerBaseModel],
    configs: list[frontend_models.DFEColumnConfigBase],
    sample_data: pd.DataFrame,
    read_table_name: str | None = None,
    pre_filled_data: dict[str, Any] | None = None,
) -> None:
    """Render a single DFE tab with add/filter buttons and a dataframe editor."""
    add_btn = add_button.AddButton(
        table_name=table_name,
        backend_model=backend_model,
        pre_filled_data=pre_filled_data,
    )
    filter_btn = filter_button.FilterButton(table_name=table_name)

    writable_configs = [
        c for c in configs if isinstance(c, frontend_models.DFEColumnConfig)
    ]

    filter_col, _, add_col = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)
    with add_col:
        new_data_added = add_btn(col_configs=writable_configs)
    with filter_col:
        filters_changed, configs = filter_btn(col_configs=configs)

    base_dfe.DFE(table_name=table_name, configs=configs).load_input_data(
        sample_data,
        filters_changed=filters_changed,
        new_data_added=new_data_added,
        read_table_name=read_table_name,
    ).render()
