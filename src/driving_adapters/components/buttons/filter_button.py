"""Filter button: a dialog that stores per-column filters for a grid in session.

The applied filters live in session state under ``{key_prefix}_col_configs`` and
are read back by ``grid.build_working_df`` via ``grid_sync.apply_active_filters``.
"""

import datetime
import typing

import streamlit as st

from domain import query
from driving_adapters import ss_keys
from driving_adapters.components.buttons import constants

if typing.TYPE_CHECKING:
    from driving_adapters.models import frontend_models

_CSS_ACTIVE = """
    button {
        background-color: rgba(33, 195, 84, 0.1);
        border: 1px solid rgba(33, 195, 84, 0.3);
    }
"""


def _column_values(
    grid_source: "frontend_models.GridSource",
    column_name: str,
) -> set[object]:
    """Return the existing values for a column via the grid data source."""
    if grid_source.data_source is None:
        msg = "Filtering requires a data source to read column values."
        raise ValueError(msg)
    return grid_source.data_source.unique_values(column_name)


def _get_min_max_values(
    grid_source: "frontend_models.GridSource",
    column_name: str,
) -> tuple[float, float]:
    """Return the min and max of a numeric column's existing values."""
    col_vals = [v for v in _column_values(grid_source, column_name) if v is not None]
    min_value = float(min(col_vals)) if col_vals else 0.0
    max_value = float(max(col_vals)) if col_vals else 1.0
    return (min_value, max_value)


def _handle_date_filtering(
    key_prefix: str,
    col_config: "frontend_models.DFEColumnConfig",
) -> query.Filters | None:
    """Render a date-range filter input and return the chosen filter."""
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
        key=f"{key_prefix}_filter_date_{col_config.column_name}",
    )

    if isinstance(selected_dates, tuple):
        date_tuple = typing.cast("tuple[datetime.date, ...]", selected_dates)
        if len(date_tuple) > 1:
            return query.Filters(gte=date_tuple[0], lte=date_tuple[1])
        if len(date_tuple) == 1:
            return query.Filters(gte=date_tuple[0], lte=date_tuple[0])
    return None


def _handle_numeric_filtering(
    grid_source: "frontend_models.GridSource",
    col_config: "frontend_models.DFEColumnConfig",
) -> query.Filters | None:
    """Render a numeric-range slider filter and return the chosen filter."""
    default_min, default_max = _get_min_max_values(grid_source, col_config.column_name)
    if default_min == default_max:
        return None

    step = (default_max - default_min) / 100
    selected_values = st.slider(
        label=f"Filter by {col_config.button_label or col_config.column_name}",
        min_value=default_min,
        max_value=default_max,
        value=(default_min, default_max),
        step=step,
        key=f"{grid_source.key_prefix}_filter_numeric_{col_config.column_name}",
    )
    if selected_values == (default_min, default_max):
        return None
    return query.Filters(gte=selected_values[0], lte=selected_values[1])


def _handle_multiselect_filtering(
    key_prefix: str,
    col_config: "frontend_models.DFEColumnConfig",
    unique_values: set[object],
) -> query.Filters | None:
    """Render a multiselect filter for a low-cardinality column."""
    default_selected: set[object] = set()
    if col_config.filters:
        if col_config.filters.in_:
            default_selected = set(col_config.filters.in_)
        elif col_config.filters.eq is not None:
            default_selected = {col_config.filters.eq}
        elif col_config.filters.contains:
            substr = str(col_config.filters.contains).lower()
            default_selected = {v for v in unique_values if substr in str(v).lower()}
        default_selected &= unique_values

    label = f"Filter by {col_config.button_label or col_config.column_name}"
    default = list(default_selected) if default_selected else None
    key = f"{key_prefix}_filter_selectbox_{col_config.column_name}"
    if col_config.format_func:
        selected_values = st.multiselect(
            label,
            options=unique_values,
            default=default,
            format_func=col_config.format_func,
            key=key,
        )
    else:
        selected_values = st.multiselect(
            label,
            options=unique_values,
            default=default,
            key=key,
        )

    if not selected_values:
        return None
    # The selected column values are domain filter values at runtime.
    return query.Filters(in_=typing.cast("list[query.FilterValue]", selected_values))


def _handle_generic_filtering(
    key_prefix: str,
    col_config: "frontend_models.DFEColumnConfig",
) -> query.Filters | None:
    """Render a text-contains filter input and return the chosen filter."""
    user_text_input = st.text_input(
        label=f"Filter by {col_config.button_label or col_config.column_name}",
        value=col_config.filters.eq if col_config.filters else "",
        key=f"{key_prefix}_filter_text_{col_config.column_name}",
    )
    return query.Filters(contains=user_text_input) if user_text_input else None


@st.dialog("Filter Columns")
def _filter_dialog(
    grid_source: "frontend_models.GridSource",
    grid_display: "frontend_models.GridDisplay",
) -> None:
    """Render the per-column filter dialog and store the result on apply.

    Streamlit struggles to return values from dialogs, so the chosen configs are
    written to session state under the grid's key prefix.
    """
    col_configs = list(grid_display.columns)
    key_prefix = grid_source.key_prefix
    display_name = key_prefix.replace("_", " ").title()
    st.write(f"Filter **{display_name}** by:")
    for col_config in col_configs:
        if not col_config.visible:
            continue
        if col_config.input_widget == st.date_input:
            col_config.filters = _handle_date_filtering(key_prefix, col_config)
        elif col_config.input_widget == st.number_input:
            col_config.filters = _handle_numeric_filtering(grid_source, col_config)
        elif (
            unique_vals := _column_values(grid_source, col_config.column_name)
        ) and len(
            unique_vals,
        ) < constants.MAX_UNIQUE_VALUES:
            col_config.filters = _handle_multiselect_filtering(
                key_prefix,
                col_config,
                unique_vals,
            )
        else:
            col_config.filters = _handle_generic_filtering(key_prefix, col_config)

    if st.button("Apply Filtering", key=f"{key_prefix}_apply_filtering_button"):
        st.session_state[f"{key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}"] = col_configs
        st.rerun()


def render_filter_button(
    grid_source: "frontend_models.GridSource",
    grid_display: "frontend_models.GridDisplay",
) -> None:
    """Render the filter button; opens the filter dialog when clicked.

    The button is highlighted while any column carries a filter.
    """
    key_prefix = grid_source.key_prefix
    # Read the applied filters from session (what the dialog stored), not the
    # freshly rebuilt default columns — otherwise a grid with default filters is
    # always highlighted and clearing them never turns it off.
    active_configs = st.session_state.get(
        f"{key_prefix}_{ss_keys.SSKeys.COL_CONFIGS}",
        grid_display.columns,
    )
    active = any(col.filters is not None for col in active_configs)
    css = _CSS_ACTIVE if active else ""

    container_key = f"{key_prefix}_filter_button_container"
    with st.container(key=container_key):
        if st.button(
            label="",
            icon=constants.ButtonIcons.FILTER,
            key=f"{key_prefix}_filter_button",
        ):
            _filter_dialog(grid_source, grid_display)
    st.markdown(
        f"<style>.st-key-{container_key} {css}</style>",
        unsafe_allow_html=True,
    )
