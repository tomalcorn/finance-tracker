"""Module for the SortButton class.

Handles the rendering of the SortButton. When clicked, displays a dialog
allowing users to select sorting options for each column in a table. Takes column
configs as input and saves the updated configs with sorting options to session state
before returning them. On subsequent calls, retrieves the configs from session state
if available.
"""

import typing

import streamlit as st

import ss_keys
from libs.buttons import base_button, constants
from libs.models import frontend_models


class SortButton(base_button.BaseButton):
    """Class representing a sort button."""

    def __init__(
        self,
        table_name: str,
    ) -> None:
        """Initialize the SortButton instance."""
        super().__init__(table_name)

    def _current_css_style(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> str:
        """Get the current CSS style based on whether sorting is applied."""
        if any(col_config.sorting is not None for col_config in col_configs):
            return self.css_style_active
        return self.css_style_normal

    @st.dialog("Sort Columns")
    def _sorting_button_dialog(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Render the sorting button dialog.

        Streamlit struggles with returning values from dialogs, so we store the configs
        in the session state.
        """
        st.write(f"Sort **{self._table_name}** by:")
        for col_config in col_configs:
            current_sort = col_config.sorting
            options: list[str | None] = ["asc", "desc", None]

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

            col_config.sorting = typing.cast(
                "constants.SortingValues | None",
                sort_order,
            )
        # Store configs in session state
        if st.button("Apply Sorting", key=f"{self._table_name}_apply_sorting_button"):
            st.session_state[f"{self._table_name}_{ss_keys.SSKeys.COL_CONFIGS}"] = (
                col_configs
            )
            st.rerun()

    def __call__(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> list[frontend_models.DFEColumnConfig]:
        """Render the sort button in the UI.

        Args:
            col_configs: The current column configurations.

        Returns:
            If clicked and sorting options selected, returns updated column configs.
            Otherwise, returns the original column configs.

        """
        _key = f"{self._table_name}_sort_button_container"
        st.markdown(
            f"<style>.st-key-{_key} {self._current_css_style(col_configs)}</style>",
            unsafe_allow_html=True,
        )
        with st.container(key=_key):
            if st.button(
                label="Sort",
                icon="↕️",
                key=f"{self._table_name}_sort_button",
                use_container_width=True,
            ):
                self._sorting_button_dialog(col_configs)
        returned_configs: list[frontend_models.DFEColumnConfig] = st.session_state.get(
            f"{self._table_name}_{ss_keys.SSKeys.COL_CONFIGS}",
            col_configs,
        )
        return returned_configs
