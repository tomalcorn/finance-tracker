"""Module for the FilterButton class."""

import typing

import streamlit as st
from streamlit_extras import stylable_container

from src.libs import config, constants, utils
from src.libs.buttons import base


class FilterButton(base.BaseButton):
    """Class representing a 'Filter' button in the UI."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[config.DFEColumnConfig],
    ) -> None:
        """Initialize the FilterButton instance."""
        super().__init__(table_name, col_configs)

    def _current_css_style(self) -> str:
        """Get the current CSS style based on whether filtering is applied."""
        if any(col_config.filtering is not None for col_config in self._col_configs):
            return self.css_style_active
        return self.css_style_normal

    def _handle_date_filtering(
        self,
        col_config: config.DFEColumnConfig,
    ) -> config.Filters | None:
        """Handle filtering for date columns."""
        if col_config.filtering:
            default_dates = (col_config.filtering.gte, col_config.filtering.lte)
        else:
            default_dates = utils.get_start_and_end_of_month()

        selected_dates = st.date_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=default_dates,
            key=f"{self._table_name}_filter_date_{col_config.column_name}",
        )

        if isinstance(selected_dates, tuple) and len(selected_dates) > 1:
            return config.Filters(
                gte=selected_dates[0].isoformat(),
                lte=selected_dates[1].isoformat(),
            )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 1:
            return config.Filters(
                gte=selected_dates[0].isoformat(),
                lte=selected_dates[0].isoformat(),
            )
        return None

    def _handle_numeric_filtering(
        self,
        col_config: config.DFEColumnConfig,
    ) -> config.Filters | None:
        """Handle filtering for numeric columns."""
        if col_config.filtering:
            default_min = col_config.filtering.gte
            default_max = col_config.filtering.lte
        else:
            default_min, default_max = utils.get_min_max_values(
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
            return None

        return config.Filters(gte=selected_values[0], lte=selected_values[1])

    def _handle_selectbox_filtering(
        self,
        col_config: config.DFEColumnConfig,
        unique_values: set[typing.Any],
    ) -> config.Filters | None:
        """Handle filtering using a selectbox for columns with limited unique values."""
        # Safely get default selected values
        default_selected: set[typing.Any] = set()
        if col_config.filtering:
            default_selected = set(col_config.filtering.eq or col_config.filtering.in_)
            default_selected &= unique_values

        selected_values = st.multiselect(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            options=unique_values,
            default=list(default_selected) if default_selected else None,
            key=f"{self._table_name}_filter_selectbox_{col_config.column_name}",
        )
        return config.Filters(in_=selected_values) if selected_values else None

    def _handle_generic_filtering(
        self,
        col_config: config.DFEColumnConfig,
    ) -> config.Filters | None:
        """Handle generic filtering using a text input."""
        user_text_input = st.text_input(
            label=f"Filter by {col_config.button_label or col_config.column_name}",
            value=col_config.filtering.eq if col_config.filtering else "",
            key=f"{self._table_name}_filter_text_{col_config.column_name}",
        )
        return config.Filters(contains=user_text_input) if user_text_input else None

    @st.dialog("Filter Columns")
    def _filtering_button_dialog(self) -> None:
        """Render the filtering button dialog.

        Streamlit struggles with returning values from dialogs, so we store the configs
        in the session state.
        """
        st.write(f"Filter **{self._table_name}** by:")
        for col_config in self._col_configs:
            if col_config.input_widget == st.date_input:
                col_config.filtering = self._handle_date_filtering(col_config)
            elif col_config.input_widget == st.number_input:
                col_config.filtering = self._handle_numeric_filtering(col_config)
            elif (
                unique_vals := utils.get_unique_values(
                    self._table_name,
                    col_config.column_name,
                )
            ) and len(unique_vals) < constants.MAX_UNIQUE_VALUES:
                col_config.filtering = self._handle_selectbox_filtering(
                    col_config,
                    unique_vals,
                )
            else:
                col_config.filtering = self._handle_generic_filtering(col_config)

        # Store configs in session state
        if st.button(
            "Apply Filtering",
            key=f"{self._table_name}_apply_filtering_button",
        ):
            st.session_state[f"{self._table_name}_{constants.SSKeys.COL_CONFIGS}"] = (
                self._col_configs
            )
            st.rerun()

    def __call__(self) -> list[config.DFEColumnConfig]:
        """Render the filter button in the UI.

        Returns:
            If clicked and filtering options selected, returns updated column configs.
            Otherwise, returns the original column configs.

        """
        with stylable_container.stylable_container(
            key=f"{self._table_name}_filter_button_container",
            css_styles=self._current_css_style(),
        ):
            if st.button(
                label="Filter",
                icon="🔍",
                key=f"{self._table_name}_filter_button",
            ):
                self._filtering_button_dialog()
        returned_configs: list[config.DFEColumnConfig] = st.session_state.get(
            f"{self._table_name}_{constants.SSKeys.COL_CONFIGS}",
            self._col_configs,
        )
        return returned_configs
