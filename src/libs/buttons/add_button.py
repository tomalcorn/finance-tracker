"""Module for the AddButton class."""

import typing

import streamlit as st

from libs import frontend_models
from libs.buttons import base_button


class AddButton(base_button.BaseButton):
    """Class representing an 'Add' button in the UI."""

    def __init__(
        self,
        table_name: str,
    ) -> None:
        """Initialize the AddButton instance."""
        self._table_name = table_name

    def _submit_new_row(self, new_row: dict[str, typing.Any]) -> None:
        """Handle the submission of a new row."""
        msg = "This method should be implemented to handle new row submission."
        raise NotImplementedError(msg)

    @st.dialog("Add Row")
    def _add_button_dialog(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Render the 'Add' button dialog."""
        st.write(f"Add a new row to {self._table_name}")
        outputs = [
            col.input_widget(
                label=col.button_label or col.column_name,
                key=f"{self._table_name}_new_row_{col.column_name}",
                **col.input_kwargs,
            )
            for col in col_configs
        ]
        options_unfilled = any(output is None or output == "" for output in outputs)
        submit_button = st.button(
            label="Submit",
            key=f"{self._table_name}_submit_new_row_button",
            disabled=options_unfilled,
        )
        if submit_button:
            new_row = {
                col.column_name: output
                for col, output in zip(col_configs, outputs, strict=False)
            }
            self._submit_new_row(new_row)

    def __call__(self, col_configs: list[frontend_models.DFEColumnConfig]) -> None:
        """Render the 'Add' button in the UI."""
        if st.button(
            label="New",
            icon="➕",  # noqa: RUF001
            key=f"{self._table_name}_add_row_button",
            use_container_width=True,
        ):
            self._add_button_dialog(col_configs)
