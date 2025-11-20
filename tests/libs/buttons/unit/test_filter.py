"""Unit tests for the filter button."""

import datetime
from unittest import mock

import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from src.libs import config, utils
from src.libs.buttons import filter  # noqa: A004
from tests import conftest


def _filter_button_dialog_wrapper() -> None:
    """Call the _filtering_button_dialog method."""
    import streamlit as st
    from src.libs import config
    from src.libs.buttons import filter  # noqa: A004

    # Mock utils.get_unique_values to return test data
    with mock.patch.object(utils, "get_unique_values") as mock_func:
        mock_func.return_value = {"value1", "value2", "value3"}

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
                filtering=config.Filters(gte=10, lte=100),
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


@pytest.fixture(name="filter_button")
def _filter_button(
    col_configs: list[config.DFEColumnConfig],
) -> filter.FilterButton:
    return filter.FilterButton("test_table", col_configs)


def test_current_css_style_no_filtering(
    col_configs: list[config.DFEColumnConfig],
) -> None:
    """Test _current_css_style returns normal style when no filtering applied."""
    # Arrange
    filter_button = filter.FilterButton("test_table_1", col_configs)

    # Act
    result = filter_button._current_css_style()

    # Assert
    assert result == filter_button.css_style_normal


def test_current_css_style_with_filtering(
    col_configs: list[config.DFEColumnConfig],
) -> None:
    """Test _current_css_style returns active style when filtering is applied."""
    # Arrange
    col_configs[0].filtering = config.Filters(contains="test")
    filter_button = filter.FilterButton("test_table_1", col_configs)

    # Act
    result = filter_button._current_css_style()

    # Assert
    assert result == filter_button.css_style_active


class TestFilterButtonDialog:
    """Tests for the FilterButton dialog method."""

    def test_filtering_button_dialog_text_renders(
        self,
        app_tester: st_test.AppTest,
    ) -> None:
        """Test that the filtering button dialog renders text without errors."""
        # Arrange
        exptected_dialog_text = "Filter **test_table** by:"
        expected_multiselect_label = "Filter by col1"
        expected_multiselect_options = ["value1", "value2", "value3"]
        exptected_slider_text = "Filter by col2"
        expected_slider_min, expected_slider_max = 10, 100
        # Act
        app_tester.run()

        # Assert
        actual_multiselect_label = app_tester.multiselect[0].label
        actual_multiselect_options = app_tester.multiselect[0].options
        actual_slider_label = app_tester.slider[0].label
        actual_slider_min = app_tester.slider[0].min
        actual_slider_max = app_tester.slider[0].max
        assert all(
            [
                exptected_dialog_text in conftest.get_rendered_texts(app_tester),
                actual_multiselect_label == expected_multiselect_label,
                set(actual_multiselect_options) == set(expected_multiselect_options),
                actual_slider_label == exptected_slider_text,
                actual_slider_min == expected_slider_min,
                actual_slider_max == expected_slider_max,
            ],
        )


class TestFilterHandling:
    """Tests for filter handling methods."""

    def test_handle_date_filtering_no_filtering(
        self,
        filter_button: filter.FilterButton,
    ) -> None:
        """Test _handle_date_filtering returns None when no filtering applied."""
        # Arrange
        date_col_config = config.DFEColumnConfig(
            column_name="date_col",
            column_config={},
            input_widget=st.date_input,
            filtering=None,
        )

        # Act
        result = filter_button._handle_date_filtering(date_col_config)

        # Assert
        assert result is None

    def test_handle_date_filtering_with_filtering(self) -> None:
        """Test _handle_date_filtering returns Filters when filtering is applied.

        Have to mock streamlit date input because impossible to return config from app
        tester.
        """
        # Arrange
        with mock.patch.object(st, "date_input") as mock_date_input:
            mock_date_input.return_value = (
                datetime.date(2024, 1, 1),
                datetime.date(2024, 1, 31),
            )

            filter_button = filter.FilterButton("test_table", [])

            date_col_config = config.DFEColumnConfig(
                column_name="date_col",
                column_config={},
                input_widget=st.date_input,
                filtering=config.Filters(
                    gte=datetime.date(2023, 1, 1),
                    lte=datetime.date(2023, 1, 31),
                ),
            )

            # Act
            result = filter_button._handle_date_filtering(date_col_config)

            # Assert
            assert result == config.Filters(
                gte=datetime.date(2024, 1, 1),
                lte=datetime.date(2024, 1, 31),
            )
