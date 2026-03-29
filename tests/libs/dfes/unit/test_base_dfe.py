"""Unit tests for the base_dfe module."""

from unittest import mock

import pandas as pd
import pytest

from libs import data_client
from libs.dfes import base_dfe


@pytest.fixture(name="input_df")
def _input_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"col1": [1, 2], "col2": [3, 4]},
    )


class TestDFE:
    """Tests for the DFE class."""

    def test_clear_working_df(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test clearing the working dataframe."""
        # Arrange
        dfe_instance.working_df = input_df.copy()

        # Act
        dfe_instance._clear_working_df()

        # Assert
        assert dfe_instance.working_df is None

    def test_load_input_data_no_change_to_configs(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test loading input data when there is no change to configs."""
        # Arrange
        sample_data = input_df.copy()
        # Changing just to show sample data does nothing
        sample_data.loc[0, "col1"] = 10
        dfe_instance.working_df = input_df.copy()

        # Act
        dfe_instance.load_input_data(
            input_df,
            filters_changed=False,
            new_data_added=False,
        )

        # Assert
        if dfe_instance.working_df is None:
            msg = "working_df is None, expected DataFrame to match input_df"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe_instance.working_df, input_df)

    def test_load_input_data_with_change_to_configs_loads_new_data(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test loading input data when there is a change to configs."""
        # Arrange - modify sample data and return input_df from data_client
        sample_data = input_df.copy()
        sample_data.loc[0, "col1"] = 10
        modified_df = input_df.copy()
        modified_df.loc[0, "col1"] = 20

        dfe_instance.working_df = input_df.copy()

        # mock get_data to return different data on successive calls
        mock_get_data = mock.patch.object(
            data_client,
            "get_data",
            return_value=modified_df,
        )
        with mock_get_data:
            # Act
            dfe_instance.load_input_data(
                sample_data,
                filters_changed=True,
                new_data_added=False,
            )

        # Assert
        if dfe_instance.working_df is None:
            msg = "working_df is None, expected modified DataFrame"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe_instance.working_df, modified_df)

    def test_load_input_data_get_data_returns_empty_df(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test loading input data when get_data returns an empty dataframe."""
        # Arrange - mock get_data to return empty dataframe
        sample_data = input_df.copy()
        sample_data.loc[0, "col1"] = 10
        mock_get_data = mock.patch.object(
            data_client,
            "get_data",
            return_value=pd.DataFrame(),
        )
        with mock_get_data:
            # Act
            dfe_instance.load_input_data(
                sample_data,
                filters_changed=False,
                new_data_added=False,
            )

        # Assert
        if dfe_instance.working_df is None:
            msg = "working_df is None, expected empty DataFrame"
            raise AssertionError(msg)

        pd.testing.assert_frame_equal(dfe_instance.working_df, sample_data)

    def test_enforce_unique_cols_no_duplicates(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols when there are no duplicates."""
        # Arrange
        row = {"name": "New Item", "value": 100}
        unique_col_names = ["name"]

        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Other Item", "Different Item"],
        ):
            # Act
            result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        assert result == {"name": "New Item", "value": 100}

    def test_enforce_unique_cols_duplicate_without_suffix(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols when duplicate exists without suffix."""
        # Arrange
        row = {"name": "Item", "value": 100}
        unique_col_names = ["name"]

        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item", "Other Item"],
        ):
            # Act
            result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        assert result == {"name": "Item (1)", "value": 100}

    def test_enforce_unique_cols_duplicate_with_suffix(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols when duplicates exist with suffixes."""
        # Arrange
        row = {"name": "Item", "value": 100}
        unique_col_names = ["name"]

        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item", "Item (1)", "Item (2)", "Other Item"],
        ):
            # Act
            result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        assert result == {"name": "Item (3)", "value": 100}

    def test_enforce_unique_cols_with_existing_suffix(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols when row value already has a suffix."""
        # Arrange
        row = {"name": "Item (5)", "value": 100}
        unique_col_names = ["name"]

        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item", "Item (1)", "Item (2)"],
        ):
            # Act
            result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        # Should strip the (5), find duplicates with base "Item", and use max suffix + 1
        assert result == {"name": "Item (3)", "value": 100}

    def test_enforce_unique_cols_column_not_in_row(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols when unique column is not in row."""
        # Arrange
        row = {"value": 100}
        unique_col_names = ["name"]

        # Act - no need to mock since column not in row
        result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        assert result == {"value": 100}

    def test_enforce_unique_cols_non_sequential_suffixes(
        self,
        dfe_instance: base_dfe.DFE,
    ) -> None:
        """Test _enforce_unique_cols with non-sequential suffix numbers."""
        # Arrange
        row = {"name": "Item", "value": 100}
        unique_col_names = ["name"]

        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item", "Item (2)", "Item (5)", "Item (10)"],
        ):
            # Act
            result = dfe_instance._enforce_unique_cols(row, unique_col_names)

        # Assert
        # Should find max suffix (10) and add 1
        assert result == {"name": "Item (11)", "value": 100}
