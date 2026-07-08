"""Unit tests for the filter button free functions."""

import datetime
from unittest import mock

import pandas as pd
import pydantic
import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from driving_adapters.components.buttons import filter_button
from driving_adapters.models import frontend_models
from tests import conftest

from domain import query


class _StubModel(pydantic.BaseModel):
    pass


class _StubDataSource:
    """GridDataSource stub returning a fixed set of column values."""

    def __init__(self, column_values: set[object] | None = None) -> None:
        self._column_values = column_values or set()

    def rows(self) -> list[pydantic.BaseModel]:
        return []

    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return self._column_values

    def apply(self, changes: object) -> None:
        """No-op; filter tests never write."""


def _config(unique_values: set[object] | None = None) -> frontend_models.DFEConfig:
    """Build a minimal grid config whose data source yields ``unique_values``."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(write_table="test_table"),
        backend_model=_StubModel,
        configs=[],
        sample_data=pd.DataFrame(),
        data_source=_StubDataSource(unique_values),
        read_via_repository=True,
    )


@pytest.mark.parametrize(
    ("column_values", "expected_min", "expected_max"),
    [
        ({10, 20, 30, 40, 50}, 10, 50),
        ({-5, 0, 5, 10}, -5, 10),
        ({0.1, 0.5, 0.9}, 0.1, 0.9),
        (set(), 0.0, 1.0),
    ],
)
def test_get_min_max_values(
    column_values: set[object],
    expected_min: float,
    expected_max: float,
) -> None:
    """Test _get_min_max_values returns correct min and max values."""
    # Act
    min_value, max_value = filter_button._get_min_max_values(
        _config(column_values),
        "test_numeric_column",
    )

    # Assert
    assert all([min_value == expected_min, max_value == expected_max])


def _filter_dialog_wrapper(config: "frontend_models.DFEConfig") -> None:
    """Render the filter dialog for AppTest (config injected via kwargs)."""
    import streamlit as st  # noqa: F401 - needed for app_test from_function
    from driving_adapters.components.buttons import filter_button

    filter_button._filter_dialog(config)


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    dialog_configs = [
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
    config = frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(write_table="test_table"),
        backend_model=_StubModel,
        configs=dialog_configs,
        sample_data=pd.DataFrame(),
        data_source=_StubDataSource({0.88, 0.23, 0.1}),
        read_via_repository=True,
    )
    return st_test.AppTest.from_function(
        _filter_dialog_wrapper,
        default_timeout=120,
        kwargs={"config": config},
    )


def test_filter_dialog_renders(app_tester: st_test.AppTest) -> None:
    """Test that the filter dialog renders its widgets without errors."""
    # Arrange
    expected_slider_min, expected_slider_max = 0.1, 0.88

    # Act
    app_tester.run()

    # Assert
    assert all(
        [
            "Filter **Test Table** by:" in conftest.get_rendered_texts(app_tester),
            app_tester.multiselect[0].label == "Filter by col1",
            set(app_tester.multiselect[0].options) == {"0.88", "0.23", "0.1"},
            app_tester.slider[0].label == "Filter by col2",
            app_tester.slider[0].min == expected_slider_min,
            app_tester.slider[0].max == expected_slider_max,
        ],
    )


class TestFilterHandling:
    """Tests for the individual filter-handling functions."""

    def test_handle_date_filtering_no_filtering(self) -> None:
        """_handle_date_filtering returns None when no range is chosen."""
        # Arrange
        date_col_config = frontend_models.DFEColumnConfigBase(
            column_name="date_col",
            column_config={},
            input_widget=st.date_input,
            filters=None,
        )

        # Act
        result = filter_button._handle_date_filtering(_config(), date_col_config)

        # Assert
        assert result is None

    def test_handle_date_filtering_with_filtering(self) -> None:
        """_handle_date_filtering returns Filters for the chosen date range."""
        # Arrange
        with mock.patch.object(st, "date_input") as mock_date_input:
            mock_date_input.return_value = (
                datetime.date(2024, 1, 1),
                datetime.date(2024, 1, 31),
            )
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
            result = filter_button._handle_date_filtering(_config(), date_col_config)

        # Assert
        assert result == query.Filters(
            gte=datetime.date(2024, 1, 1),
            lte=datetime.date(2024, 1, 31),
        )

    def test_handle_numeric_filtering_no_filtering(self) -> None:
        """_handle_numeric_filtering returns None when the slider is unchanged."""
        # Arrange
        with (
            mock.patch.object(
                filter_button,
                "_get_min_max_values",
                return_value=(0.0, 100.0),
            ),
            mock.patch.object(st, "slider", return_value=(0.0, 100.0)),
        ):
            numeric_col_config = frontend_models.DFEColumnConfigBase(
                column_name="numeric_col",
                column_config={},
                input_widget=st.number_input,
                filters=None,
            )

            # Act
            result = filter_button._handle_numeric_filtering(
                _config(),
                numeric_col_config,
            )

        # Assert
        assert result is None

    def test_handle_numeric_filtering_with_filtering(self) -> None:
        """_handle_numeric_filtering returns Filters for the chosen range."""
        # Arrange
        with mock.patch.object(st, "slider", return_value=(20.0, 80.0)):
            numeric_col_config = frontend_models.DFEColumnConfigBase(
                column_name="numeric_col",
                column_config={},
                input_widget=st.number_input,
                filters=query.Filters(gte=10.0, lte=100.0),
            )

            # Act
            result = filter_button._handle_numeric_filtering(
                _config({10.0, 90.0}),
                numeric_col_config,
            )

        # Assert
        assert result == query.Filters(gte=20.0, lte=80.0)

    def test_handle_multiselect_filtering_no_filtering(self) -> None:
        """_handle_multiselect_filtering returns None when nothing is selected."""
        # Arrange
        select_col_config = frontend_models.DFEColumnConfigBase(
            column_name="select_col",
            column_config={},
            input_widget=st.multiselect,
            filters=None,
        )

        # Act
        result = filter_button._handle_multiselect_filtering(
            _config(),
            select_col_config,
            {"value1", "value2", "value3"},
        )

        # Assert
        assert result is None

    def test_handle_multiselect_filtering_with_filtering(self) -> None:
        """_handle_multiselect_filtering returns Filters for the selection."""
        # Arrange
        with mock.patch.object(st, "multiselect", return_value=["value1", "value3"]):
            select_col_config = frontend_models.DFEColumnConfigBase(
                column_name="select_col",
                column_config={},
                input_widget=st.multiselect,
                filters=query.Filters(in_=["value2"]),
            )

            # Act
            result = filter_button._handle_multiselect_filtering(
                _config(),
                select_col_config,
                {"value1", "value2", "value3"},
            )

        # Assert
        assert result == query.Filters(in_=["value1", "value3"])

    def test_handle_generic_filtering_no_filtering(self) -> None:
        """_handle_generic_filtering returns None when the text box is empty."""
        # Arrange
        generic_col_config = frontend_models.DFEColumnConfigBase(
            column_name="generic_col",
            column_config={},
            input_widget=st.text_input,
            filters=None,
        )

        # Act
        result = filter_button._handle_generic_filtering(_config(), generic_col_config)

        # Assert
        assert result is None

    def test_handle_generic_filtering_with_filtering(self) -> None:
        """_handle_generic_filtering returns a contains-Filter for the text."""
        # Arrange
        with mock.patch.object(st, "text_input", return_value="new_filter"):
            generic_col_config = frontend_models.DFEColumnConfigBase(
                column_name="generic_col",
                column_config={},
                input_widget=st.text_input,
                filters=query.Filters(contains="old_filter"),
            )

            # Act
            result = filter_button._handle_generic_filtering(
                _config(),
                generic_col_config,
            )

        # Assert
        assert result == query.Filters(contains="new_filter")
