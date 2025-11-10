"""Module for the SortButton class."""

import streamlit as st

from src.libs import config
from src.libs.buttons import base


class SortButton(base.BaseButton):
    """Class representing a sort button."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[config.DFEColumnConfig],
    ) -> None:
        """Initialize the SortButton instance."""
        super().__init__()
        self._table_name = table_name
        self._col_configs = col_configs

    @st.dialog("Sort Columns")
    def _sorting_button_dialog(self) -> None:
        """Render the sorting button dialog."""
