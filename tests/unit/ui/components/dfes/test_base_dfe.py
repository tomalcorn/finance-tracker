"""Unit tests for the base_dfe module."""

from unittest import mock

import pandas as pd
import pydantic
import pytest
import streamlit as st

from ui import data_client, ss_keys
from ui.components.dfes import base_dfe
from ui.models import frontend_models


class _StubModel(pydantic.BaseModel):
    pass


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

    def test_load_input_data_no_reload_when_working_df_exists(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test that load_input_data does not reload when working_df already exists."""
        # Arrange
        dfe_instance.working_df = input_df.copy()

        # Act
        dfe_instance.load_input_data()

        # Assert - working_df unchanged
        if dfe_instance.working_df is None:
            msg = "working_df is None, expected DataFrame to match input_df"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe_instance.working_df, input_df)

    def test_load_input_data_loads_when_working_df_is_none(
        self,
        dfe_instance: base_dfe.DFE,
        input_df: pd.DataFrame,
    ) -> None:
        """Test that load_input_data fetches data when working_df is None."""
        # Arrange
        mock_get_data = mock.patch.object(
            data_client,
            "get_data",
            return_value=input_df,
        )
        with mock_get_data:
            # Act
            dfe_instance.load_input_data()

        # Assert
        if dfe_instance.working_df is None:
            msg = "working_df is None, expected loaded DataFrame"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe_instance.working_df, input_df)

    def test_load_input_data_uses_sample_data_when_get_data_empty(
        self,
        input_df: pd.DataFrame,
    ) -> None:
        """Test load_input_data falls back to sample_data when get_data is empty."""
        # Arrange - create DFE with sample_data
        sample_data = input_df.copy()
        sample_data.loc[0, "col1"] = 10
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(write_table="users"),
                backend_model=_StubModel,
                configs=[],
                sample_data=sample_data,
            ),
        )
        mock_get_data = mock.patch.object(
            data_client,
            "get_data",
            return_value=pd.DataFrame(),
        )
        with mock_get_data:
            # Act
            dfe.load_input_data()

        # Assert
        if dfe.working_df is None:
            msg = "working_df is None, expected sample_data fallback"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe.working_df, sample_data)

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


class TestDFEKeyPrefix:
    """Tests for DFE key_prefix behaviour."""

    def test_key_prefix_defaults_to_write_table(self) -> None:
        """Test that key_prefix defaults to write_table when not provided."""
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(write_table="payments"),
                backend_model=_StubModel,
                configs=[],
                sample_data=pd.DataFrame(),
            ),
        )
        assert dfe.key_prefix == "payments"

    def test_key_prefix_uses_provided_value(self) -> None:
        """Test that key_prefix uses the provided value."""
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="payments",
                    key_prefix="income_entries",
                ),
                backend_model=_StubModel,
                configs=[],
                sample_data=pd.DataFrame(),
            ),
        )
        assert dfe.key_prefix == "income_entries"

    def test_session_state_keys_use_key_prefix(self) -> None:
        """Test that session state keys use key_prefix, not write_table."""
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="payments",
                    key_prefix="income_entries",
                ),
                backend_model=_StubModel,
                configs=[],
                sample_data=pd.DataFrame(),
            ),
        )
        test_df = pd.DataFrame({"col1": [1]})
        dfe.working_df = test_df

        expected_key = f"income_entries_{ss_keys.SSKeys.WORKING_DF}"
        wrong_key = f"payments_{ss_keys.SSKeys.WORKING_DF}"
        assert expected_key in st.session_state
        assert wrong_key not in st.session_state
        pd.testing.assert_frame_equal(st.session_state[expected_key], test_df)


class TestApplyColumnFilter:
    """Tests for the _apply_column_filter static method."""

    def test_eq_filter_on_string_column(self) -> None:
        """Test equality filter on a string column."""
        df = pd.DataFrame({"payment_type": ["expense", "income", "expense"]})
        result = base_dfe.DFE._apply_column_filter(df, "payment_type", "==", "expense")
        assert list(result["payment_type"]) == ["expense", "expense"]

    def test_eq_filter_no_matches(self) -> None:
        """Test equality filter returns empty when no matches."""
        df = pd.DataFrame({"payment_type": ["expense", "expense"]})
        result = base_dfe.DFE._apply_column_filter(df, "payment_type", "==", "income")
        assert result.empty

    def test_contains_filter(self) -> None:
        """Test contains filter on a string column."""
        df = pd.DataFrame({"name": ["test item", "other", "test thing"]})
        result = base_dfe.DFE._apply_column_filter(df, "name", "contains", "test")
        expected_count = 2
        assert len(result) == expected_count

    def test_gte_lte_filter_on_numeric(self) -> None:
        """Test >= and <= filters on a numeric column."""
        df = pd.DataFrame({"value": [10, 20, 30, 40, 50]})
        result = base_dfe.DFE._apply_column_filter(df, "value", ">=", 20)
        result = base_dfe.DFE._apply_column_filter(result, "value", "<=", 40)
        assert list(result["value"]) == [20, 30, 40]
