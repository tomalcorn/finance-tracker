"""Unit tests for the filter button."""

import pytest
import streamlit.testing.v1 as st_test


def _filter_button_dialog_wrapper() -> None:
    """Call the _filtering_button_dialog method."""
    import streamlit as st
    from src.libs import config
    from src.libs.buttons import filter  # noqa: A004

    dfe_configs = [
        config.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            filtering=config.Filters(contains="test"),
        ),
        config.DFEColumnConfig(
            column_name="col2",
            column_config={},
            input_widget=st.number_input,
            filtering=config.Filters(gt=10),
        ),
    ]

    filter_button = filter.FilterButton("test_table", dfe_configs)

    return filter_button._filtering_button_dialog()


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _filter_button_dialog_wrapper,
        default_timeout=120,
    )
