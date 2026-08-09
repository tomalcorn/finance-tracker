"""Unit tests for the grid config models' validators."""

from typing import TYPE_CHECKING

import pandas as pd
import pydantic
import pytest
import streamlit as st

from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

_WIDTH = 115


@pytest.fixture(name="build_display")
def _build_display() -> "Callable[..., frontend_models.GridDisplay]":
    """Return a builder for a one-column grid display."""

    def _build(
        column_config: object,
        *,
        total: bool = True,
    ) -> frontend_models.GridDisplay:
        return frontend_models.GridDisplay(
            columns=[
                frontend_models.DFEColumnConfig(
                    column_name="cost",
                    column_config=column_config,
                    input_widget=st.number_input,
                    total=total,
                ),
            ],
            sample_data=pd.DataFrame({"cost": [0.0]}),
        )

    return _build


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


def test_a_totalled_grid_must_size_its_visible_columns(
    build_display: "Callable[..., frontend_models.GridDisplay]",
) -> None:
    # Arrange - the strip is a second table beneath the grid, and Streamlit sizes
    # a column to its content, so without a declared width the two drift apart.
    column_config = st.column_config.NumberColumn("Cost", format="£%.2f")

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="must declare a width"):
        build_display(column_config)


def test_a_grid_without_totals_needs_no_widths(
    build_display: "Callable[..., frontend_models.GridDisplay]",
) -> None:
    # Arrange - nothing sits beneath it, so its columns can size themselves.
    column_config = st.column_config.NumberColumn("Cost", format="£%.2f")

    # Act
    display = build_display(column_config, total=False)

    # Assert
    assert display.columns[0].column_config["width"] is None
