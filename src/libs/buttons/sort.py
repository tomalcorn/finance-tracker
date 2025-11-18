"""Module for the SortButton class.

Handles the rendering of the SortButton. When clicked, displays a dialog
allowing users to select sorting options for each column in a table. Takes column
configs as input and saves the updated configs with sorting options to session state
before returning them. On subsequent calls, retrieves the configs from session state
if available.
"""

import streamlit as st
from streamlit_extras import stylable_container

from src.libs import config, models
from src.libs.buttons import base


class SortButton(base.BaseButton):
    """Class representing a sort button."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[config.DFEColumnConfig],
    ) -> None:
        """Initialize the SortButton instance."""
        super().__init__(table_name, col_configs)

    def _current_css_style(self) -> str:
        """Get the current CSS style based on whether sorting is applied."""
        if any(col_config.sorting is not None for col_config in self._col_configs):
            return self.css_style_active
        return self.css_style_normal

    @st.dialog("Sort Columns")
    def _sorting_button_dialog(self) -> None:
        """Render the sorting button dialog.

        Streamlit struggles with returning values from dialogs, so we store the configs
        in the session state.
        """
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
        # Store configs in session state
        if st.button("Apply Sorting", key=f"{self._table_name}_apply_sorting_button"):
            st.session_state[f"{self._table_name}_{models.SSKeys.COL_CONFIGS}"] = (
                self._col_configs
            )
            st.rerun()

    def __call__(self) -> list[config.DFEColumnConfig]:
        """Render the sort button in the UI.

        Returns:
            If clicked and sorting options selected, returns updated column configs.
            Otherwise, returns the original column configs.

        """
        with stylable_container.stylable_container(
            key=f"{self._table_name}_sort_button_container",
            css_styles=self._current_css_style(),
        ):
            if st.button(
                label="Sort",
                icon="↕️",
                key=f"{self._table_name}_sort_button",
            ):
                self._sorting_button_dialog()
        returned_configs: list[config.DFEColumnConfig] = st.session_state.get(
            f"{self._table_name}_{models.SSKeys.COL_CONFIGS}",
            self._col_configs,
        )
        return returned_configs
