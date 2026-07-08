"""Add-row button: a dialog that writes a new row through the grid port."""

import logging
import typing

import pydantic
import streamlit as st

from domain import entities
from driving_adapters import auth
from driving_adapters.components.buttons import constants

if typing.TYPE_CHECKING:
    from driving_adapters.models import frontend_models

logger = logging.getLogger(__name__)


def _has_unfilled_required(
    col_configs: list["frontend_models.DFEColumnConfig"],
    outputs: list[object],
) -> bool:
    """Return whether any required column has an unfilled output."""
    return any(
        (output is None or output == "")
        for col, output in zip(col_configs, outputs, strict=False)
        if col.required
    )


def _submit_new_row(
    config: "frontend_models.DFEConfig",
    new_row: dict[str, object],
) -> None:
    """Validate a new row and write it through the grid data source.

    Raises:
        ValueError: If the row fails validation, or the grid has no data source
            to write through.

    """
    try:
        new_row["user_id"] = auth.get_current_user()
        new_row.update(config.extra_row_values or {})
        model_instance = config.backend_model.model_validate(new_row)
    except pydantic.ValidationError as e:
        msg = f"Invalid data for new row in {config.write_table}: {e}"
        raise ValueError(msg) from e
    if config.data_source is None:
        msg = "An editable grid requires a data source to add rows."
        raise ValueError(msg)
    config.data_source.apply(
        entities.BackendUpdates(
            added_rows=[model_instance.model_dump(mode="json", exclude_none=True)],
        ),
    )


@st.dialog("Add Row")
def _add_row_dialog(config: "frontend_models.DFEConfig") -> None:
    """Render the add-row dialog and submit the row on confirm."""
    col_configs = config.writable_configs
    display_name = config.key_prefix.replace("_", " ").title()
    st.write(f"Add a new row to {display_name}")
    outputs = [
        col.input_widget(
            label=col.button_label or col.column_name,
            key=f"{config.key_prefix}_new_row_{col.column_name}",
            **col.input_kwargs,
        )
        for col in col_configs
    ]
    submit_button = st.button(
        label="Submit",
        key=f"{config.key_prefix}_submit_new_row_button",
        disabled=_has_unfilled_required(col_configs, outputs),
    )
    if submit_button:
        new_row = {
            col.column_name: output
            for col, output in zip(col_configs, outputs, strict=False)
        }
        try:
            _submit_new_row(config, new_row)
        except ValueError:
            logger.exception("Failed to add a new row to %s", config.write_table)
            st.error("Could not add the row. Please check the values and try again.")
            return
        st.rerun()


def render_add_button(config: "frontend_models.DFEConfig") -> None:
    """Render the add-row button; opens the add dialog when clicked.

    A submitted row is applied immediately through the port, so the rerun the
    dialog triggers rebuilds the grid with the new row already present.
    """
    if st.button(
        label="",
        icon=constants.ButtonIcons.ADD,
        key=f"{config.key_prefix}_add_row_button",
    ):
        _add_row_dialog(config)
