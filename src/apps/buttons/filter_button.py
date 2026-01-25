"""Module for the FilterButton class."""

import typing

import streamlit as st
from streamlit_extras import stylable_container

from apps import data_client
from libs.buttons import base_button
from libs.models import constants, frontend_models


class FilterButton(base_button.BaseButton):
    """Class representing a 'Filter' button in the UI."""

    def __init__(
        self,
        table_name: str,
    ) -> None:
        """Initialize the FilterButton instance."""
        super().__init__(table_name)

    @property
    def column_configs(self) -> list[frontend_models.DFEColumnConfig]:
        """Get the current column configurations from session state."""
        return st.session_state.get(
            f"{self._table_name}_{constants.SSKeys.COL_CONFIGS}",
            [],
        )

    @column_configs.setter
    def column_configs(
        self,
        configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Set the column configurations in session state."""
        st.session_state[f"{self._table_name}_{constants.SSKeys.COL_CONFIGS}"] = configs

    def _current_css_style(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
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
        col_config: frontend_models.DFEColumnConfig,
    ) -> frontend_models.Filters | None:
        """Handle filtering for date columns."""
        default_dates = None
        if col_config.filters:
            default_dates = (col_config.filters.gte, col_config.filters.lte)

        selected_dates = st.date_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=default_dates,
            key=f"{self._table_name}_filter_date_{col_config.column_name}",
        )

        if isinstance(selected_dates, tuple) and len(selected_dates) > 1:
            return frontend_models.Filters(
                gte=selected_dates[0],
                lte=selected_dates[1],
            )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 1:
            return frontend_models.Filters(
                gte=selected_dates[0],
                lte=selected_dates[0],
            )
        return None

    def _handle_numeric_filtering(
        self,
        col_config: frontend_models.DFEColumnConfig,
    ) -> frontend_models.Filters | None:
        """Handle filtering for numeric columns."""
        default_min, default_max = self._get_min_max_values(
            self._table_name,
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
            key=f"{self._table_name}_filter_numeric_{col_config.column_name}",
        )

        if selected_values == (default_min, default_max):
            return None  # No change in filtering

        return frontend_models.Filters(gte=selected_values[0], lte=selected_values[1])

    def _handle_multiselect_filtering(
        self,
        col_config: frontend_models.DFEColumnConfig,
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

        selected_values = st.multiselect(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            options=unique_values,
            default=list(default_selected) if default_selected else None,
            key=f"{self._table_name}_filter_selectbox_{col_config.column_name}",
        )
        return frontend_models.Filters(in_=selected_values) if selected_values else None

    def _handle_generic_filtering(
        self,
        col_config: frontend_models.DFEColumnConfig,
    ) -> frontend_models.Filters | None:
        """Handle generic filtering using a text input."""
        user_text_input = st.text_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=col_config.filters.eq if col_config.filters else "",
            key=f"{self._table_name}_filter_text_{col_config.column_name}",
        )
        return (
            frontend_models.Filters(contains=user_text_input)
            if user_text_input
            else None
        )

    @st.dialog("Filter Columns")
    def _filtering_button_dialog(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Render the filtering button dialog.

        Streamlit struggles with returning values from dialogs, so we store the configs
        in the session state.
        """
        st.write(f"Filter **{self._table_name}** by:")
        for col_config in col_configs:
            if col_config.input_widget == st.date_input:
                col_config.filters = self._handle_date_filtering(col_config)
            elif col_config.input_widget == st.number_input:
                col_config.filters = self._handle_numeric_filtering(col_config)
            elif (
                unique_vals := set(
                    data_client.get_column_values(
                        self._table_name,
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
            key=f"{self._table_name}_apply_filtering_button",
        ):
            self.column_configs = col_configs
            st.rerun()

    def __call__(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> list[frontend_models.DFEColumnConfig]:
        """Render the filter button in the UI.

        Args:
            col_configs: The current column configurations.

        Returns:
            If clicked and filtering options selected, returns updated column configs.
            Otherwise, returns the original column configs.

        """
        with stylable_container.stylable_container(
            key=f"{self._table_name}_filter_button_container",
            css_styles=self._current_css_style(col_configs),
        ):
            if st.button(
                label="Filter",
                icon="🔍",
                key=f"{self._table_name}_filter_button",
                use_container_width=True,
            ):
                self._filtering_button_dialog(col_configs)

        return self.column_configs or col_configs
