"""Unit tests for the totals strip beneath a grid."""

from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest
import streamlit as st
import streamlit.testing.v1 as st_test

from driving_adapters.components.dfes import totals
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(name="build_column")
def _build_column() -> "Callable[..., frontend_models.DFEColumnConfig]":
    """Return a builder for one column config.

    A test overrides only what it varies — whether the column is totalled,
    shown, or a number at all — and inherits the rest.
    """

    def _build(
        column_name: str,
        column_config: Any = None,  # noqa: ANN401 - Streamlit's own config type
        *,
        total: bool = False,
        visible: bool = True,
    ) -> frontend_models.DFEColumnConfig:
        return frontend_models.DFEColumnConfig(
            column_name=column_name,
            column_config=column_config
            or st.column_config.NumberColumn(column_name.title(), format="£%.2f"),
            input_widget=st.number_input,
            total=total,
            visible=visible,
        )

    return _build


@pytest.fixture(name="build_display")
def _build_display(
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
) -> "Callable[..., frontend_models.GridDisplay]":
    """Return a builder for a grid display over a name column plus given columns."""

    def _build(
        *columns: frontend_models.DFEColumnConfig,
        show_name: bool = True,
    ) -> frontend_models.GridDisplay:
        name_column = build_column(
            "name",
            st.column_config.TextColumn("Name"),
            visible=show_name,
        )
        return frontend_models.GridDisplay(
            columns=[name_column, *columns],
            sample_data=pd.DataFrame({"name": ["Example"]}),
        )

    return _build


@pytest.fixture(name="working_df")
def _working_df() -> pd.DataFrame:
    """Provide a display frame of two persisted rows."""
    return pd.DataFrame(
        [
            {"id": "uuid-0", "name": "Holiday", "cost": 100.0, "banked": 25.0},
            {"id": "uuid-1", "name": "Bike", "cost": 50.0, "banked": 10.0},
        ],
    )


def test_only_the_flagged_columns_are_summed(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
    working_df: pd.DataFrame,
) -> None:
    # Arrange
    display = build_display(
        build_column("cost", total=True),
        build_column("banked"),
    )

    # Act
    totals_df = totals.build_totals_df(display, working_df)

    # Assert
    expected = pd.DataFrame([{"name": "Total", "cost": 150.0, "banked": ""}])
    pd.testing.assert_frame_equal(totals_df, expected)


def test_a_hidden_column_is_not_totalled(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
    working_df: pd.DataFrame,
) -> None:
    # Arrange - a hidden column has no column above the strip to sit under, so
    # its total would be a figure with nothing to relate it to.
    display = build_display(build_column("cost", total=True, visible=False))

    # Act
    totals_df = totals.build_totals_df(display, working_df)

    # Assert
    assert totals_df.empty


def test_no_strip_when_no_column_is_flagged(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
    working_df: pd.DataFrame,
) -> None:
    # Arrange
    display = build_display(build_column("cost"))

    # Act
    totals_df = totals.build_totals_df(display, working_df)

    # Assert
    assert totals_df.empty


def test_no_strip_over_the_empty_state_sample_data(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
) -> None:
    # Arrange - the port returned no rows, so the grid shows sample data (no id
    # column); totalling the example figures would read as real money.
    display = build_display(build_column("cost", total=True))
    sample_data = pd.DataFrame([{"name": "Example One-Off", "cost": 0.0}])

    # Act
    totals_df = totals.build_totals_df(display, sample_data)

    # Assert
    assert totals_df.empty


def test_the_row_is_named_in_the_first_blank_column(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
    working_df: pd.DataFrame,
) -> None:
    # Arrange - the leading column is summed here, so the label has to fall
    # through to the next blank one rather than displace a figure.
    display = build_display(
        build_column("cost", total=True),
        build_column("banked"),
        show_name=False,
    )

    # Act
    totals_df = totals.build_totals_df(display, working_df)

    # Assert
    expected = pd.DataFrame([{"cost": 150.0, "banked": "Total"}])
    pd.testing.assert_frame_equal(totals_df, expected)


def test_a_summed_column_keeps_the_grids_own_config(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
) -> None:
    # Arrange - the figure is formatted and sized like the column above it.
    cost = build_column("cost", total=True)
    display = build_display(cost)

    # Act
    column_config = totals.build_column_config(display)

    # Assert
    assert column_config["cost"] == cost.column_config


def test_a_blank_column_is_re_declared_as_text(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
) -> None:
    # Arrange - a blank cell in a number column renders as "None", so the
    # columns that are not summed are re-declared as text, keeping their label.
    display = build_display(build_column("cost", total=True), build_column("banked"))

    # Act
    column_config = totals.build_column_config(display)

    # Assert
    assert column_config["banked"] == st.column_config.TextColumn("Banked")


def _render_wrapper(grid_display, working_df) -> None:  # noqa: ANN001
    """Render a grid's editor for AppTest.

    The arguments are injected via AppTest ``kwargs`` because from_function
    re-runs this body in a fresh namespace where module-level names aren't
    visible.
    """
    from driving_adapters.components.dfes import grid

    grid.render_editor(grid_display, "test_table", working_df)


def test_the_strip_is_rendered_beneath_the_editor(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
    working_df: pd.DataFrame,
) -> None:
    # Arrange - the strip follows the editor itself, so a block composing its
    # own button row around the editor still gets it.
    app_tester = st_test.AppTest.from_function(
        _render_wrapper,
        default_timeout=120,
        kwargs={
            "grid_display": build_display(build_column("cost", total=True)),
            "working_df": working_df,
        },
    )

    # Act
    app_tester.run()

    # Assert - the editor is the first frame on the page, the strip the second
    assert list(app_tester.dataframe[1].value.iloc[0]) == ["Total", 150.0]


def test_a_hidden_column_is_left_out_of_the_config(
    build_display: "Callable[..., frontend_models.GridDisplay]",
    build_column: "Callable[..., frontend_models.DFEColumnConfig]",
) -> None:
    # Arrange
    display = build_display(
        build_column("cost", total=True),
        build_column("banked", visible=False),
    )

    # Act
    column_config = totals.build_column_config(display)

    # Assert
    assert "banked" not in column_config
