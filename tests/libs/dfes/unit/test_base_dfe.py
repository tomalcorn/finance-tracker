"""Unit tests for the base_dfe module."""

import pandas as pd
import pytest

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
        dfe_instance.previous_configs = [
            model.model_copy(deep=True) for model in dfe_instance.configs
        ]

        # Act
        dfe_instance.load_input_data(input_df)

        # Assert
        pd.testing.assert_frame_equal(dfe_instance.working_df, input_df)
