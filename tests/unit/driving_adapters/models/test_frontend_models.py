"""Unit tests for the grid config models' validators."""

import pydantic
import pytest
import streamlit as st

from driving_adapters.models import frontend_models


def test_a_text_column_cannot_be_totalled() -> None:
    # Arrange - the strip sums the column, so a non-numeric one would show a
    # meaningless 0.00 under it rather than fail loudly here.
    column_config = st.column_config.TextColumn("Name")

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="cannot be totalled"):
        frontend_models.DFEColumnConfig(
            column_name="name",
            column_config=column_config,
            input_widget=st.text_input,
            total=True,
        )


@pytest.mark.parametrize(
    "column_config",
    [
        st.column_config.NumberColumn("Cost", format="£%.2f"),
        st.column_config.ProgressColumn("Split", format="%.1f%%"),
    ],
)
def test_a_numeric_column_can_be_totalled(column_config: object) -> None:
    # Arrange / Act
    column = frontend_models.DFEColumnConfig(
        column_name="cost",
        column_config=column_config,
        input_widget=st.number_input,
        total=True,
    )

    # Assert
    assert column.total
