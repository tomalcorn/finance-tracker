"""Module for the AddButton class."""

import streamlit as st


class AddButton:
    """Class representing an 'Add' button in the UI."""

    def __init__(self, table_name: str) -> None:
        """Initialize the AddButton instance."""
        self._table_name = table_name

    @st.dialog("Add Row")
    def _add_button_dialog(self) -> None:
        """Render the 'Add' button dialog."""

    def __call__(self) -> None:
        """Render the 'Add' button in the UI."""
        if st.button(
            label="New",
            icon="➕",  # noqa: RUF001
            key=f"{self._table_name}_add_row_button",
        ):
            self._add_button_dialog()


add_button = AddButton("finance_tracker_table")
with st.container():
    add_button()
