"""Free-function dataframe-editor grid: build, render, and commit through the port.

Replaces the old ``base_dfe.DFE`` class. State lives where Streamlit already
keeps it — the widget's own ``st.session_state[key]`` deltas and the filter
``col_configs`` — so there is no parallel ``working_df`` / ``backend_updates``
store. ``grid_sync`` stays the pure delta-translation layer.

The flow is commit-at-top: the dashboard applies each grid's pending edits
(``commit``) before rendering, then ``render`` rebuilds the frame from the port.
"""

import contextlib

import pandas as pd
import streamlit as st

from ui import ss_keys
from ui.components.buttons import add_button, constants, filter_button
from ui.components.dfes import grid_sync
from ui.models import frontend_models


def _active_configs(
    config: frontend_models.DFEConfig,
) -> list[frontend_models.DFEColumnConfigBase]:
    """Return the column configs with the current filter state from session."""
    key = f"{config.key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}"
    return st.session_state.get(key, list(config.configs))


def _convert_cols_to_datetime(
    dataframe: pd.DataFrame,
    configs: list[frontend_models.DFEColumnConfigBase],
) -> pd.DataFrame:
    """Convert columns to date/datetime based on their column config type."""
    for config in configs:
        col = config.column_name
        if col not in dataframe.columns or not isinstance(config.column_config, dict):
            continue
        col_type = config.column_config.get("type_config", {}).get("type")
        if col_type == "date":
            with contextlib.suppress(Exception):
                dataframe[col] = pd.to_datetime(dataframe[col]).dt.date
        elif col_type == "datetime":
            with contextlib.suppress(Exception):
                dataframe[col] = pd.to_datetime(dataframe[col])
    return dataframe


def build_working_df(config: frontend_models.DFEConfig) -> pd.DataFrame:
    """Build the display frame from the port, applying the active filters.

    Reads display rows from ``data_source.rows()`` (Path A) and filters them in
    Python, falling back to the config's sample data when the read is empty.
    Rebuilt every run — there is no cached working frame in session state.
    """
    if config.read_via_repository and config.data_source is not None:
        rows = config.data_source.rows()
        working_df = pd.DataFrame([row.model_dump(mode="json") for row in rows])
        working_df = grid_sync.apply_active_filters(working_df, _active_configs(config))
    else:
        working_df = pd.DataFrame()
    if working_df.empty:
        working_df = config.sample_data.copy()
    working_df = _convert_cols_to_datetime(working_df, list(config.configs))
    return grid_sync.apply_active_sorting(working_df, _active_configs(config))


def render_editor(config: frontend_models.DFEConfig, working_df: pd.DataFrame) -> None:
    """Render the ``st.data_editor`` widget for a grid.

    No ``on_change`` callback: the widget records its edits in
    ``st.session_state[key]`` and triggers a rerun; ``commit`` reads those
    deltas at the top of that run.
    """
    st.data_editor(
        working_df,
        key=config.key_prefix,
        column_config={cfg.column_name: cfg.column_config for cfg in config.configs},
        column_order=[col.column_name for col in config.configs if col.visible],
        num_rows=config.num_rows,
        hide_index=True,
    )


def render_buttons(config: frontend_models.DFEConfig) -> None:
    """Render the add and filter buttons above a grid.

    Both buttons open dialogs that ``st.rerun`` on change, so the next run's
    ``build_working_df`` already reflects any add or filter — there is no
    working frame to refresh in place.
    """
    if config.num_rows != "fixed":
        add_col, filter_col, _ = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)
        with add_col:
            add_button.render_add_button(config)
        with filter_col:
            filter_button.render_filter_button(config)
    else:
        filter_col, _ = st.columns([1, 5])
        with filter_col:
            filter_button.render_filter_button(config)


def render(config: frontend_models.DFEConfig) -> None:
    """Render a full grid: buttons, then the editor over the current frame.

    The default block flow. Blocks that need a custom button row (e.g. the
    one-offs "bank it" button) compose ``build_working_df`` / ``render_editor``
    and the button functions directly instead.
    """
    render_buttons(config)
    render_editor(config, build_working_df(config))


def commit(config: frontend_models.DFEConfig) -> None:
    """Apply the grid's pending editor deltas through the port, then clear them.

    Reads the ``st.data_editor`` widget's own edited/deleted-row deltas from
    ``st.session_state[key]``, rebuilds the frame those deltas index into, maps
    them to backend writes via ``grid_sync``, and applies them through the grid
    data source. The widget deltas are then cleared so they neither re-apply on
    the next render nor double-apply on the next commit.

    A no-op when there are no pending deltas or no data source.
    """
    key = config.key_prefix
    editor_state = st.session_state.get(key)
    if not editor_state or config.data_source is None:
        return

    edited_rows = editor_state.get(ss_keys.SSKeys.EDITED_ROWS, {})
    deleted_rows = editor_state.get(ss_keys.SSKeys.DELETED_ROWS, [])
    if not edited_rows and not deleted_rows:
        return

    unique_col_names = [
        col.column_name
        for col in config.configs
        if isinstance(col, frontend_models.DFEColumnConfig) and col.enforce_unique
    ]
    updates = grid_sync.compute_backend_updates(
        working_df=build_working_df(config),
        edited_rows=edited_rows,
        deleted_rows=deleted_rows,
        unique_col_names=unique_col_names,
        unique_checker=config.data_source.unique_values,
    )
    config.data_source.apply(updates)
    del st.session_state[key]
