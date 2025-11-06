"""Module for the AddButton class."""

import streamlit as st

import config


class AddButton:
    """Class representing an 'Add' button in the UI."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[config.DFEColumnConfig],
    ) -> None:
        """Initialize the AddButton instance."""
        self._table_name = table_name
        self._col_configs = col_configs

    @st.dialog("Add Row")
    def _add_button_dialog(self) -> None:
        """Render the 'Add' button dialog."""
        st.write(f"Add a new row to {self._table_name}")
        outputs = [
            col.input_widget(
                label=col.button_label or col.column,
                key=f"{self._table_name}_new_row_{col.column}",
                **col.input_kwargs,
            )
            for col in self._col_configs
        ]
        options_unfilled = any(output is None or output == "" for output in outputs)
        submit_button = st.button(
            label="Submit",
            key=f"{self._table_name}_submit_new_row_button",
            disabled=options_unfilled,
        )
        if submit_button:
            pass

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
