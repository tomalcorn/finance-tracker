"""Unit tests for the filter button."""

import datetime
from unittest import mock

import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from tests import conftest

from domain import query
from ui.components.buttons import filter_button
from ui.models import frontend_models


def _filter_button_dialog_wrapper() -> None:
    """Call the _filtering_button_dialog method."""
    import streamlit as st

    from domain import query
    from ui.components.buttons import filter_button
    from ui.models import frontend_models

    dfe_configs = [
        frontend_models.DFEColumnConfigBase(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            filters=query.Filters(contains="test"),
        ),
        frontend_models.DFEColumnConfigBase(
            column_name="col2",
            column_config={},
            input_widget=st.number_input,
            filters=query.Filters(gte=10, lte=100),
        ),
    ]

    filter_button_instance = filter_button.FilterButton(
        "test_table",
        unique_values=lambda _column: {0.88, 0.23, 0.1},
    )

    return filter_button_instance._filtering_button_dialog(dfe_configs)


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _filter_button_dialog_wrapper,
        default_timeout=120,
    )


@pytest.fixture(name="filter_button_instance")
def _filter_button_instance() -> filter_button.FilterButton:
    return filter_button.FilterButton("test_table")


def test_current_css_style_no_filtering(
    col_configs: list[frontend_models.DFEColumnConfigBase],
) -> None:
    """Test _current_css_style returns normal style when no filtering applied."""
    # Arrange
    col_configs_no_filters = [
        col_configs[i].model_copy(update={"filters": None})
        for i in range(len(col_configs))
    ]
    filter_button_instance = filter_button.FilterButton("test_table_1")

    # Act
    result = filter_button_instance._current_css_style(col_configs_no_filters)

    # Assert
    assert result == filter_button_instance.css_style_normal


def test_current_css_style_with_filtering(
    col_configs: list[frontend_models.DFEColumnConfigBase],
) -> None:
    """Test _current_css_style returns active style when filtering is applied."""
    # Arrange
    col_configs[0].filters = query.Filters(contains="test")
    filter_button_instance = filter_button.FilterButton("test_table_1")

    # Act
    result = filter_button_instance._current_css_style(col_configs)

    # Assert
    assert result == filter_button_instance.css_style_active


@pytest.mark.parametrize(
    ("column_values", "expected_min", "expected_max"),
    [
        ({10, 20, 30, 40, 50}, 10, 50),
        ({-5, 0, 5, 10}, -5, 10),
        ({0.1, 0.5, 0.9}, 0.1, 0.9),
        (set(), 0.0, 1.0),  # Edge case: no values
    ],
)
def test_get_min_max_values(
    column_values: set[object],
    expected_min: float,
    expected_max: float,
) -> None:
    """Test _get_min_max_values returns correct min and max values."""
    instance = filter_button.FilterButton(
        "test_table",
        unique_values=lambda _column: column_values,
    )

    # Act
    min_value, max_value = instance._get_min_max_values(
        column_name="test_numeric_column",
    )

    # Assert
    assert all(
        [
            min_value == expected_min,
            max_value == expected_max,
        ],
    )


class TestFilterButtonDialog:
    """Tests for the FilterButton dialog method."""

    def test_filtering_button_dialog_text_renders(
        self,
        app_tester: st_test.AppTest,
    ) -> None:
        """Test that the filtering button dialog renders text without errors."""
        # Arrange
        exptected_dialog_text = "Filter **Test Table** by:"
        expected_multiselect_label = "Filter by col1"
        expected_multiselect_options = ["0.88", "0.23", "0.1"]
        exptected_slider_text = "Filter by col2"
        expected_slider_min, expected_slider_max = 0.1, 0.88
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
        filter_button_instance: filter_button.FilterButton,
    ) -> None:
        """Test _handle_date_filtering returns None when no filtering applied."""
        # Arrange
        date_col_config = frontend_models.DFEColumnConfigBase(
            column_name="date_col",
            column_config={},
            input_widget=st.date_input,
            filters=None,
        )

        # Act
        result = filter_button_instance._handle_date_filtering(date_col_config)

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

            filter_button_instance = filter_button.FilterButton("test_table")

            date_col_config = frontend_models.DFEColumnConfigBase(
                column_name="date_col",
                column_config={},
                input_widget=st.date_input,
                filters=query.Filters(
                    gte=datetime.date(2023, 1, 1),
                    lte=datetime.date(2023, 1, 31),
                ),
            )

            # Act
            result = filter_button_instance._handle_date_filtering(date_col_config)

            # Assert
            assert result == query.Filters(
                gte=datetime.date(2024, 1, 1),
                lte=datetime.date(2024, 1, 31),
            )

    def test_handle_numeric_filtering_no_filtering(
        self,
        filter_button_instance: filter_button.FilterButton,
    ) -> None:
        """Test _handle_numeric_filtering returns None when no filtering applied."""
        # Arrange
        with (
            mock.patch.object(
                filter_button.FilterButton,
                "_get_min_max_values",
            ) as mock_get_min_max,
            mock.patch.object(st, "slider") as mock_slider,
        ):
            mock_get_min_max.return_value = (0.0, 100.0)
            mock_slider.return_value = (0.0, 100.0)
            numeric_col_config = frontend_models.DFEColumnConfigBase(
                column_name="numeric_col",
                column_config={},
                input_widget=st.number_input,
                filters=None,
            )

            # Act
            result = filter_button_instance._handle_numeric_filtering(
                numeric_col_config,
            )

            # Assert
            assert result is None

    def test_handle_numeric_filtering_with_filtering(self) -> None:
        """Test _handle_numeric_filtering returns Filters when filtering is applied.

        Have to mock streamlit slider because impossible to return config from app
        tester.
        """
        # Arrange
        with mock.patch.object(st, "slider") as mock_slider:
            mock_slider.return_value = (20.0, 80.0)

            filter_button_instance = filter_button.FilterButton(
                "test_table",
                unique_values=lambda _column: {10.0, 90.0},
            )

            numeric_col_config = frontend_models.DFEColumnConfigBase(
                column_name="numeric_col",
                column_config={},
                input_widget=st.number_input,
                filters=query.Filters(gte=10.0, lte=100.0),
            )

            # Act
            result = filter_button_instance._handle_numeric_filtering(
                numeric_col_config,
            )

            # Assert
            assert result == query.Filters(gte=20.0, lte=80.0)

    def test_handle_multiselect_filtering_no_filtering(
        self,
        filter_button_instance: filter_button.FilterButton,
    ) -> None:
        """Test _handle_multiselect_filtering returns None when no filtering applied."""
        # Arrange
        select_col_config = frontend_models.DFEColumnConfigBase(
            column_name="select_col",
            column_config={},
            input_widget=st.multiselect,
            filters=None,
        )
        unique_values = {"value1", "value2", "value3"}

        # Act
        result = filter_button_instance._handle_multiselect_filtering(
            col_config=select_col_config,
            unique_values=unique_values,
        )

        # Assert
        assert result is None

    def test_handle_multiselect_filtering_with_filtering(self) -> None:
        """Test _handle_multiselect_filtering returns Filters when filtering is applied.

        Have to mock streamlit multiselect because impossible to return config from app
        tester.
        """
        # Arrange
        with mock.patch.object(st, "multiselect") as mock_multiselect:
            mock_multiselect.return_value = ["value1", "value3"]

            filter_button_instance = filter_button.FilterButton("test_table")
            unique_values = {"value1", "value2", "value3"}

            select_col_config = frontend_models.DFEColumnConfigBase(
                column_name="select_col",
                column_config={},
                input_widget=st.multiselect,
                filters=query.Filters(in_=["value2"]),
            )

            # Act
            result = filter_button_instance._handle_multiselect_filtering(
                col_config=select_col_config,
                unique_values=unique_values,
            )

            # Assert
            assert result == query.Filters(in_=["value1", "value3"])

    def test_generic_filtering_no_filtering(
        self,
        filter_button_instance: filter_button.FilterButton,
    ) -> None:
        """Test _handle_generic_filtering returns None when no filtering applied."""
        # Arrange
        generic_col_config = frontend_models.DFEColumnConfigBase(
            column_name="generic_col",
            column_config={},
            input_widget=st.text_input,
            filters=None,
        )

        # Act
        result = filter_button_instance._handle_generic_filtering(generic_col_config)

        # Assert
        assert result is None

    def test_handle_generic_filtering_with_filtering(self) -> None:
        """Test _handle_generic_filtering returns Filters when filtering is applied.

        Have to mock streamlit text_input because impossible to return config from app
        tester.
        """
        # Arrange
        with mock.patch.object(st, "text_input") as mock_text_input:
            mock_text_input.return_value = "new_filter"

            filter_button_instance = filter_button.FilterButton("test_table")

            generic_col_config = frontend_models.DFEColumnConfigBase(
                column_name="generic_col",
                column_config={},
                input_widget=st.text_input,
                filters=query.Filters(contains="old_filter"),
            )

            # Act
            result = filter_button_instance._handle_generic_filtering(
                generic_col_config,
            )

            # Assert
            assert result == query.Filters(contains="new_filter")
