"""Module for the FilterButton class."""

import datetime
import typing

import streamlit as st

from ui import data_client, ss_keys
from ui.components.buttons import base_button, constants
from ui.models import frontend_models


class FilterButton(base_button.BaseButton):
    """Class representing a 'Filter' button in the UI."""

    def __init__(
        self,
        table_name: str,
        key_prefix: str | None = None,
        read_table: str | None = None,
    ) -> None:
        """Initialize the FilterButton instance."""
        super().__init__(table_name)
        self._key_prefix = key_prefix or table_name
        self._read_table = read_table or table_name

    @property
    def column_configs(self) -> list[frontend_models.DFEColumnConfigBase]:
        """Get the current column configurations from session state."""
        return st.session_state.get(
            f"{self._key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}",
            [],
        )

    @column_configs.setter
    def column_configs(
        self,
        configs: list[frontend_models.DFEColumnConfigBase],
    ) -> None:
        """Set the column configurations in session state."""
        st.session_state[f"{self._key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}"] = configs

    @property
    def previous_column_configs(
        self,
    ) -> list[frontend_models.DFEColumnConfigBase] | None:
        """Get the previous column configurations from session state."""
        prev_column_configs_key = f"{self._key_prefix}_{ss_keys.SSKeys.PREV_CONFIGS}"
        return st.session_state.get(prev_column_configs_key, None)

    @previous_column_configs.setter
    def previous_column_configs(
        self,
        configs: list[frontend_models.DFEColumnConfigBase],
    ) -> None:
        """Set the previous column configurations in session state."""
        prev_column_configs_key = f"{self._key_prefix}_{ss_keys.SSKeys.PREV_CONFIGS}"
        st.session_state[prev_column_configs_key] = configs

    def _current_css_style(
        self,
        col_configs: list[frontend_models.DFEColumnConfigBase],
    ) -> str:
        """Get the current CSS style based on whether filtering is applied."""
        if any(col_config.filters is not None for col_config in col_configs):
            return self.css_style_active
        return self.css_style_normal

    def _get_min_max_values(
        self,
        table_name: str,
        column_name: str,
    ) -> tuple[float, float]:
        """Get min and max values for numeric columns using pandas."""
        col_vals = data_client.get_column_values(table_name, column_name)
        min_value = float(col_vals.min()) if not col_vals.empty else 0.0
        max_value = float(col_vals.max()) if not col_vals.empty else 1.0
        return (min_value, max_value)

    def _handle_date_filtering(
        self,
        col_config: frontend_models.DFEColumnConfigBase,
    ) -> frontend_models.Filters | None:
        """Handle filtering for date columns."""
        default_dates = None
        if col_config.filters:
            gte = col_config.filters.gte
            lte = col_config.filters.lte
            gte_date = gte if isinstance(gte, datetime.date) else None
            lte_date = lte if isinstance(lte, datetime.date) else None
            if gte_date is not None or lte_date is not None:
                default_dates = (gte_date, lte_date)

        selected_dates = st.date_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=default_dates,
            key=f"{self._key_prefix}_filter_date_{col_config.column_name}",
        )

        if isinstance(selected_dates, tuple):
            date_tuple = typing.cast("tuple[datetime.date, ...]", selected_dates)
            if len(date_tuple) > 1:
                return frontend_models.Filters(
                    gte=date_tuple[0],
                    lte=date_tuple[1],
                )
            if len(date_tuple) == 1:
                return frontend_models.Filters(
                    gte=date_tuple[0],
                    lte=date_tuple[0],
                )
        return None

    def _handle_numeric_filtering(
        self,
        col_config: frontend_models.DFEColumnConfigBase,
    ) -> frontend_models.Filters | None:
        """Handle filtering for numeric columns."""
        default_min, default_max = self._get_min_max_values(
            self._read_table,
            col_config.column_name,
        )

        if default_min == default_max:
            return None

        step = (default_max - default_min) / 100
        selected_values = st.slider(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            min_value=default_min,
            max_value=default_max,
            value=(default_min, default_max),
            step=step,
            key=f"{self._key_prefix}_filter_numeric_{col_config.column_name}",
        )

        if selected_values == (default_min, default_max):
            return None  # No change in filtering

        return frontend_models.Filters(gte=selected_values[0], lte=selected_values[1])

    def _handle_multiselect_filtering(
        self,
        col_config: frontend_models.DFEColumnConfigBase,
        unique_values: set[typing.Any],
    ) -> frontend_models.Filters | None:
        """Filter using a multiselect for columns with limited unique values."""
        # Safely get default selected values
        default_selected: set[typing.Any] = set()
        if col_config.filters:
            # Prefer 'in_' (multiple exact values), then 'eq' (single exact value),
            # then 'contains' (substring match against available unique values).
            if col_config.filters.in_:
                default_selected = set(col_config.filters.in_)
            elif col_config.filters.eq is not None:
                default_selected = {col_config.filters.eq}
            elif col_config.filters.contains:
                substr = str(col_config.filters.contains).lower()
                default_selected = {
                    v for v in unique_values if substr in str(v).lower()
                }
            else:
                default_selected = set()
            # Ensure defaults are limited to the actual unique values
            default_selected &= unique_values

        if col_config.format_func:
            selected_values = st.multiselect(
                label=f"Filter by {col_config.button_label or col_config.column_name}",
                options=unique_values,
                default=list(default_selected) if default_selected else None,
                format_func=col_config.format_func,
                key=f"{self._key_prefix}_filter_selectbox_{col_config.column_name}",
            )
        else:
            selected_values = st.multiselect(
                label=f"Filter by {col_config.button_label or col_config.column_name}",
                options=unique_values,
                default=list(default_selected) if default_selected else None,
                key=f"{self._key_prefix}_filter_selectbox_{col_config.column_name}",
            )

        return frontend_models.Filters(in_=selected_values) if selected_values else None

    def _handle_generic_filtering(
        self,
        col_config: frontend_models.DFEColumnConfigBase,
    ) -> frontend_models.Filters | None:
        """Handle generic filtering using a text input."""
        user_text_input = st.text_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=col_config.filters.eq if col_config.filters else "",
            key=f"{self._key_prefix}_filter_text_{col_config.column_name}",
        )
        return (
            frontend_models.Filters(contains=user_text_input)
            if user_text_input
            else None
        )

    @st.dialog("Filter Columns")
    def _filtering_button_dialog(
        self,
        col_configs: list[frontend_models.DFEColumnConfigBase],
    ) -> None:
        """Render the filtering button dialog.

        Streamlit struggles with returning values from dialogs, so we store the configs
        in the session state.
        """
        display_name = self._key_prefix.replace("_", " ").title()
        st.write(f"Filter **{display_name}** by:")
        for col_config in col_configs:
            if not col_config.visible:
                continue
            if col_config.input_widget == st.date_input:
                col_config.filters = self._handle_date_filtering(col_config)
            elif col_config.input_widget == st.number_input:
                col_config.filters = self._handle_numeric_filtering(col_config)
            elif (
                unique_vals := set(
                    data_client.get_column_values(
                        self._read_table,
                        col_config.column_name,
                        unique=True,
                    ),
                )
            ) and len(unique_vals) < constants.MAX_UNIQUE_VALUES:
                col_config.filters = self._handle_multiselect_filtering(
                    col_config,
                    unique_vals,
                )
            else:
                col_config.filters = self._handle_generic_filtering(col_config)

        # Store configs in session state
        if st.button(
            "Apply Filtering",
            key=f"{self._key_prefix}_apply_filtering_button",
        ):
            self.column_configs = col_configs
            st.rerun()

    def __call__(
        self,
        col_configs: list[
            frontend_models.DFEColumnConfigBase | frontend_models.DFEColumnConfig
        ],
    ) -> bool:
        """Render the filter button in the UI.

        Args:
            col_configs: The current column configurations.

        Returns:
            Whether the filters have changed since the last render.

        """
        if self.previous_column_configs is None:
            self.previous_column_configs = [
                model.model_copy(deep=True) for model in col_configs
            ]

        _key = f"{self._key_prefix}_filter_button_container"
        css = self._current_css_style(col_configs)
        with st.container(key=_key):
            if st.button(
                label="",
                icon=constants.ButtonIcons.FILTER,
                key=f"{self._key_prefix}_filter_button",
            ):
                self._filtering_button_dialog(col_configs)
        st.markdown(
            f"<style>.st-key-{_key} {css}</style>",
            unsafe_allow_html=True,
        )

        current_configs = self.column_configs or col_configs
        previous_configs = self.previous_column_configs or col_configs
        previous_configs_dumped = [c.model_dump() for c in previous_configs]
        configs_dumped = [config.model_dump() for config in current_configs]
        filters_changed = previous_configs_dumped != configs_dumped
        self.previous_column_configs = [
            model.model_copy(deep=True) for model in current_configs
        ]

        return filters_changed
