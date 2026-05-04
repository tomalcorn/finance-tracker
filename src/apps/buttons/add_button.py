"""Module for the AddButton class."""

import typing

import pydantic
import streamlit as st

from libs import data_client, ss_keys
from libs.buttons import base_button, constants
from libs.models import backend_models, backend_updates_model, frontend_models


class AddButton(base_button.BaseButton):
    """Class representing an 'Add' button in the UI."""

    def __init__(
        self,
        table_name: str,
        backend_model: type[pydantic.BaseModel],
        tables_to_clear: list | None = None,
        key_prefix: str | None = None,
    ) -> None:
        """Initialize the AddButton instance."""
        self._table_name = table_name
        self._key_prefix = key_prefix or table_name
        self._backend_model = backend_model
        self._tables_to_clear = tables_to_clear

    @property
    def new_data_added(self) -> bool:
        """Check if new data has been added in the session state."""
        return st.session_state.get(
            ss_keys.SSKeys.NEW_DATA_ADDED,
            False,
        )

    @new_data_added.setter
    def new_data_added(self, value: bool) -> None:
        """Set the new data added flag in the session state."""
        st.session_state[ss_keys.SSKeys.NEW_DATA_ADDED] = value

    def _submit_new_row(self, new_row: dict[str, typing.Any]) -> None:
        """Handle the submission of a new row."""
        try:
            current_user: backend_models.UserModel = st.session_state[
                ss_keys.SSKeys.CURRENT_USER
            ]
            new_row["user_id"] = current_user.id
            model_instance = self._backend_model.model_validate(new_row)
        except pydantic.ValidationError as e:
            msg = f"Invalid data for new row in {self._table_name}: {e}"
            raise ValueError(msg) from e
        else:
            data_client.update_backend(
                table_name=self._table_name,
                updates=backend_updates_model.BackendUpdates(
                    added_rows=[
                        model_instance.model_dump(mode="json", exclude_none=True),
                    ],
                    deleted_rows=[],
                    edited_rows={},
                ),
                tables_to_clear=self._tables_to_clear,
            )

    @st.dialog("Add Row")
    def _add_button_dialog(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Render the 'Add' button dialog."""
        display_name = self._key_prefix.replace("_", " ").title()
        st.write(f"Add a new row to {display_name}")
        outputs = [
            col.input_widget(
                label=col.button_label or col.column_name,
                key=f"{self._key_prefix}_new_row_{col.column_name}",
                **col.input_kwargs,
            )
            for col in col_configs
        ]
        options_unfilled = self._has_unfilled_required(
            col_configs,
            outputs,
        )
        submit_button = st.button(
            label="Submit",
            key=f"{self._key_prefix}_submit_new_row_button",
            disabled=options_unfilled,
        )
        if submit_button:
            new_row = {
                col.column_name: output
                for col, output in zip(col_configs, outputs, strict=False)
            }
            self._submit_new_row(new_row)
            data_client.invalidate_table_cache(self._table_name)
            self.new_data_added = True
            st.rerun()

    @staticmethod
    def _has_unfilled_required(
        col_configs: list[frontend_models.DFEColumnConfig],
        outputs: list[object],
    ) -> bool:
        """Check whether any required column has an unfilled output."""
        return any(
            (output is None or output == "")
            for col, output in zip(col_configs, outputs, strict=False)
            if col.required
        )

    def __call__(self, col_configs: list[frontend_models.DFEColumnConfig]) -> bool:
        """Render the 'Add' button in the UI.

        Returns:
            bool: True if a new row was added, False otherwise.

        """
        if st.button(
            label="",
            icon=constants.ButtonIcons.ADD,
            key=f"{self._key_prefix}_add_row_button",
        ):
            self._add_button_dialog(col_configs)
        return self.new_data_added
