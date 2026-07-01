"""Module for the base DFE classes and utilities."""

import contextlib
import typing

import pandas as pd
import streamlit as st

from domain import entities
from ui import data_client, ss_keys
from ui.components.buttons import add_button, constants, filter_button
from ui.components.dfes import data_source as data_source_mod
from ui.components.dfes import grid_sync
from ui.models import frontend_models


class DFE:
    """A self-contained dataframe editor component.

    Handles data loading, add/filter buttons, the st.data_editor widget,
    and syncing edits to the backend.
    """

    def __init__(self, config: frontend_models.DFEConfig) -> None:
        """Initialize the DFE from a config object."""
        self._config = config
        table_names = config.table_names

        self._write_table = table_names.write_table
        self._read_table = table_names.read_table or table_names.write_table
        self._key_prefix = table_names.key_prefix or table_names.write_table
        self._configs: list[frontend_models.DFEColumnConfigBase] = list(config.configs)
        self._backend_model = config.backend_model
        self._sample_data = config.sample_data
        self._num_rows = config.num_rows
        self._data_source = config.data_source
        self._read_via_repository = config.read_via_repository
        self._unique_checker: grid_sync.UniqueChecker | None = (
            config.data_source.unique_values if config.data_source else None
        )

        # Computed once — display config never changes with filter state
        self._column_config = {
            cfg.column_name: cfg.column_config for cfg in self._configs
        }

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def key_prefix(self) -> str:
        """The session state key prefix for this DFE."""
        return self._key_prefix

    @property
    def write_table(self) -> str:
        """The write table name for this DFE."""
        return self._write_table

    @property
    def working_df(self) -> pd.DataFrame | None:
        """Get the working dataframe from session state."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        return st.session_state.get(key, None)

    @working_df.setter
    def working_df(self, df: pd.DataFrame) -> None:
        """Set the working dataframe in session state."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        st.session_state[key] = df

    @property
    def backend_updates(self) -> entities.BackendUpdates:
        """Get pending backend updates for this DFE."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        return st.session_state.get(key, entities.BackendUpdates())

    @backend_updates.setter
    def backend_updates(self, updates: entities.BackendUpdates) -> None:
        key = f"{self._key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
        st.session_state[key] = updates

    @property
    def add_button(self) -> add_button.AddButton:
        """Create a configured AddButton for this DFE."""
        return add_button.AddButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            backend_model=self._backend_model,
            extra_row_values=self._config.extra_row_values,
            data_source=self._data_source,
        )

    @property
    def filter_button(self) -> filter_button.FilterButton:
        """Create a configured FilterButton for this DFE."""
        return filter_button.FilterButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            unique_values=self._unique_checker,
        )

    @property
    def writable_configs(self) -> list[frontend_models.DFEColumnConfig]:
        """Get the writable column configs for use with AddButton."""
        return [
            c
            for c in self._configs
            if isinstance(c, frontend_models.DFEColumnConfig) and c.visible
        ]

    @property
    def all_configs(self) -> list[frontend_models.DFEColumnConfigBase]:
        """Get all column configs for use with FilterButton."""
        return list(self._configs)

    # ------------------------------------------------------------------
    # Private properties
    # ------------------------------------------------------------------

    def _clear_working_df(self) -> None:
        key = f"{self._key_prefix}_{ss_keys.SSKeys.WORKING_DF}"
        if key in st.session_state:
            del st.session_state[key]

    @property
    def _active_configs(self) -> list[frontend_models.DFEColumnConfigBase]:
        """Get the active configs (with current filter state from session)."""
        key = f"{self._key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}"
        return st.session_state.get(key, self._configs)

    @property
    def _editor_state(self) -> dict[str, typing.Any]:
        return st.session_state[self._key_prefix]

    @property
    def _edited_rows(self) -> dict[str, dict[str, typing.Any]]:
        return self._editor_state[ss_keys.SSKeys.EDITED_ROWS]

    @property
    def _deleted_rows(self) -> list[int]:
        return self._editor_state[ss_keys.SSKeys.DELETED_ROWS]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_input_data(self) -> typing.Self:
        """Load data into the dataframe editor.

        Uses the active filter state from session and the sample_data from config
        as fallback when no data is returned.
        """
        if self.working_df is None:
            if self._read_via_repository and self._data_source is not None:
                rows = self._data_source.rows()
                working_df = pd.DataFrame([row.model_dump(mode="json") for row in rows])
                working_df = grid_sync.apply_active_filters(
                    working_df,
                    self._active_configs,
                )
            else:
                working_df = pd.DataFrame()
            if working_df.empty:
                working_df = self._sample_data.copy()
            working_df = self._convert_cols_to_datetime(working_df)
            self.working_df = working_df

        return self

    def render_buttons(self) -> tuple[bool, bool]:
        """Render the add and filter buttons for this DFE.

        Returns:
            A tuple of (data_added, filters_changed).

        """
        if self.working_df is None:
            msg = "Call load_input_data() before render_buttons()."
            raise ValueError(msg)

        filter_btn = filter_button.FilterButton(
            table_name=self._write_table,
            key_prefix=self._key_prefix,
            unique_values=self._unique_checker,
        )

        data_added = False
        if self._num_rows != "fixed":
            add_btn = add_button.AddButton(
                table_name=self._write_table,
                key_prefix=self._key_prefix,
                backend_model=self._backend_model,
                extra_row_values=getattr(self._config, "extra_row_values", None),
                data_source=self._data_source,
            )
            writable_configs = [
                c
                for c in self._configs
                if isinstance(c, frontend_models.DFEColumnConfig) and c.visible
            ]
            add_col, filter_col, _ = st.columns(constants.ADD_FILTER_BUTTON_WIDTHS)
            with add_col:
                data_added = add_btn(col_configs=writable_configs)
            with filter_col:
                filters_changed = filter_btn(col_configs=self._configs)
        else:
            filter_col, _ = st.columns([1, 5])
            with filter_col:
                filters_changed = filter_btn(col_configs=self._configs)

        return data_added, filters_changed

    def refresh(
        self,
        *,
        filters_changed: bool = False,
        data_added: bool = False,
    ) -> None:
        """Refresh the working dataframe if buttons triggered changes.

        Clears the cached working frame and reloads. Backend-mutating writes
        (add/edit/delete) already invalidate the affected cached reads through
        the grid port, so no separate cache bust is needed here — a filter
        change does not mutate backend data.
        """
        if filters_changed or data_added:
            self._clear_working_df()
            self.load_input_data()

    def render_editor(self) -> None:
        """Render the st.data_editor widget."""
        if self.working_df is None:
            msg = "Call load_input_data() before render_editor()."
            raise ValueError(msg)
        st.data_editor(
            self.working_df,
            key=self._key_prefix,
            column_config=self._column_config,
            column_order=[col.column_name for col in self._configs if col.visible],
            num_rows=self._num_rows,
            hide_index=True,
            on_change=self.sync,
        )

    def sync(self) -> None:
        """Prep backend updates for syncing.

        A thin caller over the pure grid_sync helpers: it pulls the editor
        deltas and active filter state out of session and hands them off.
        """
        if self.working_df is None:
            msg = "Working dataframe is not initialized. Cannot sync."
            raise ValueError(msg)

        unique_col_names = [
            col.column_name
            for col in self._configs
            if isinstance(col, frontend_models.DFEColumnConfig) and col.enforce_unique
        ]
        if unique_col_names and self._unique_checker is None:
            msg = "DFE requires a unique_values reader to enforce unique columns."
            raise ValueError(msg)
        unique_checker = self._unique_checker or (lambda _column: set())

        updates = grid_sync.compute_backend_updates(
            working_df=self.working_df,
            edited_rows=self._edited_rows,
            deleted_rows=self._deleted_rows,
            unique_col_names=unique_col_names,
            unique_checker=unique_checker,
        )

        if updates.edited_rows or updates.deleted_rows:
            filters_changed, modified_df = grid_sync.check_for_filters_updates(
                working_df=self.working_df,
                edited_rows=self._edited_rows,
                deleted_rows=self._deleted_rows,
                active_configs=self._active_configs,
            )
            if filters_changed:
                self.working_df = modified_df

        self.backend_updates = updates

    def _convert_cols_to_datetime(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to datetime/date based on column config type."""
        for config in self._configs:
            col = config.column_name
            if col not in dataframe.columns:
                continue
            if not isinstance(config.column_config, dict):
                continue
            col_type = config.column_config.get("type_config", {}).get("type")
            if col_type == "date":
                with contextlib.suppress(Exception):
                    dataframe[col] = pd.to_datetime(dataframe[col]).dt.date
            elif col_type == "datetime":
                with contextlib.suppress(Exception):
                    dataframe[col] = pd.to_datetime(dataframe[col])
        return dataframe


def commit_pending(
    data_source: data_source_mod.GridDataSource,
    key_prefix: str,
) -> None:
    """Apply and clear a grid's pending BackendUpdates through the port.

    Pops the BackendUpdates that ``DFE.sync()`` wrote to session state under
    ``key_prefix`` and hands them to the grid data source, which writes them
    and invalidates the reads they affect. An empty batch is a no-op the port
    skips.
    """
    key = f"{key_prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
    updates = st.session_state.pop(key, entities.BackendUpdates())
    data_source.apply(updates)
