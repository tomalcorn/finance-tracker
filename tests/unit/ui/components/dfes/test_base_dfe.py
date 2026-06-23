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

    def test_load_input_data_reads_via_repository(
        self,
        input_df: pd.DataFrame,
    ) -> None:
        """Test load_input_data reads display rows from the data source (Path A)."""

        class _StubDataSource:
            def load(self) -> list[dict]:
                return input_df.to_dict("records")

            def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
                return set()

        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(write_table="users"),
                backend_model=_StubModel,
                configs=[],
                sample_data=pd.DataFrame(),
                data_source=_StubDataSource(),
                read_via_repository=True,
            ),
        )

        dfe.load_input_data()

        if dfe.working_df is None:
            msg = "working_df is None, expected rows loaded from the data source"
            raise AssertionError(msg)
        pd.testing.assert_frame_equal(dfe.working_df, input_df)


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


