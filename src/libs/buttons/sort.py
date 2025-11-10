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
    def _sorting_button_dialog(self) -> list[config.DFEColumnConfig]:
        """Render the sorting button dialog."""
        st.write(f"Sort **{self._table_name}** by:")
        for col_config in self._col_configs:
            current_sort = col_config.sorting
            options = ["asc", "desc", None]

            sort_order = st.selectbox(
                label=col_config.column_name,
                options=options,
                format_func=lambda x: {
                    None: "None",
                    "asc": "Ascending",
                    "desc": "Descending",
                }[x],
                index=options.index(current_sort) if current_sort in options else None,
            )

            col_config.sorting = sort_order
        return self._col_configs

    def __call__(self) -> list[config.DFEColumnConfig] | None:
        """Render the sort button in the UI."""
        if st.button(
            label="Sort",
            icon="↕️",
            key=f"{self._table_name}_sort_button",
        ):
            return self._sorting_button_dialog()
        return None
