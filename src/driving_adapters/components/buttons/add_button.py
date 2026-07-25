"""Add-row button: a dialog that writes a new row through the grid port."""

import logging
import typing

import streamlit as st

from driving_adapters.components.buttons import constants
from ports import errors as port_errors

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
    grid_source: "frontend_models.GridSource",
    new_row: dict[str, object],
) -> None:
    """Build a new row into an entity through the port, then persist it.

    The dialog supplies only what the user typed; the data source completes the
    row with the owner and ownership it writes under and validates it, so the row
    is a complete entity before it is saved.

    Raises:
        ValueError: If the grid has no data source to write through.
        RepositoryError: If the row is not valid for the aggregate, or the write
            fails.

    """
    if grid_source.data_source is None:
        msg = "An editable grid requires a data source to add rows."
        raise ValueError(msg)
    new_row.update(grid_source.extra_row_values or {})
    data_source = grid_source.data_source
    data_source.save_entities(data_source.build_entities([new_row]))


@st.dialog("Add Row")
def _add_row_dialog(
    grid_source: "frontend_models.GridSource",
    grid_display: "frontend_models.GridDisplay",
) -> None:
    """Render the add-row dialog and submit the row on confirm."""
    col_configs = grid_display.writable_columns
    key_prefix = grid_source.key_prefix
    display_name = key_prefix.replace("_", " ").title()
    st.write(f"Add a new row to {display_name}")
    outputs = [
        col.input_widget(
            label=col.button_label or col.column_name,
            key=f"{key_prefix}_new_row_{col.column_name}",
            **col.input_kwargs,
        )
        for col in col_configs
    ]
    submit_button = st.button(
        label="Submit",
        key=f"{key_prefix}_submit_new_row_button",
        disabled=_has_unfilled_required(col_configs, outputs),
    )
    if submit_button:
        new_row = {
            col.column_name: output
            for col, output in zip(col_configs, outputs, strict=False)
        }
        try:
            _submit_new_row(grid_source, new_row)
        except (ValueError, port_errors.RepositoryError):
            logger.exception("Failed to add a new row to %s", grid_source.write_table)
            st.error("Could not add the row. Please check the values and try again.")
            return
        st.rerun()


def render_add_button(
    grid_source: "frontend_models.GridSource",
    grid_display: "frontend_models.GridDisplay",
) -> None:
    """Render the add-row button; opens the add dialog when clicked.

    A submitted row is applied immediately through the port, so the rerun the
    dialog triggers rebuilds the grid with the new row already present.
    """
    if st.button(
        label="",
        icon=constants.ButtonIcons.ADD,
        key=f"{grid_source.key_prefix}_add_row_button",
    ):
        _add_row_dialog(grid_source, grid_display)
