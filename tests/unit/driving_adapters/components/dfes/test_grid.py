"""Unit tests for the grid free functions (build_working_df + commit)."""

from typing import TYPE_CHECKING, Any

import pandas as pd
import pydantic
import streamlit as st

from driving_adapters import ss_keys
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests import conftest


class _StubModel(pydantic.BaseModel):
    pass


class _RowModel(pydantic.BaseModel):
    id: str
    name: str


def _config(
    *,
    data_source: "conftest.StubDataSource | None" = None,
    sample_data: pd.DataFrame | None = None,
    row_predicate: "Callable[[Any], bool] | None" = None,
) -> frontend_models.DFEConfig:
    """Build a minimal grid config for the tests."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table="test_table",
            data_source=data_source,
            row_predicate=row_predicate,
        ),
        display=frontend_models.GridDisplay(
            columns=[],
            sample_data=pd.DataFrame() if sample_data is None else sample_data,
        ),
    )


def test_build_working_df_reads_from_data_source(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="0", name="Alice"),
        _RowModel(id="1", name="Bob"),
    ]
    config = _config(data_source=build_stub_data_source(rows=rows))

    # Act
    working_df = grid.build_working_df(config)

    # Assert
    expected = pd.DataFrame([{"id": "0", "name": "Alice"}, {"id": "1", "name": "Bob"}])
    pd.testing.assert_frame_equal(working_df, expected)


def test_build_working_df_falls_back_to_sample_when_source_empty(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    sample = pd.DataFrame({"name": ["Example"]})
    config = _config(data_source=build_stub_data_source(rows=[]), sample_data=sample)

    # Act
    working_df = grid.build_working_df(config)

    # Assert
    pd.testing.assert_frame_equal(working_df, sample)


def test_build_working_df_without_data_source_uses_sample() -> None:
    # Arrange
    sample = pd.DataFrame({"name": ["Example"]})
    config = _config(sample_data=sample)

    # Act
    working_df = grid.build_working_df(config)

    # Assert
    pd.testing.assert_frame_equal(working_df, sample)


def test_build_working_df_narrows_rows_to_the_grids_own_slice(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - two grids share one table, so each shows only its own rows
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="0", name="Alice"),
        _RowModel(id="1", name="Bob"),
    ]
    config = _config(
        data_source=build_stub_data_source(rows=rows),
        row_predicate=lambda row: row.name == "Bob",
    )

    # Act
    working_df = grid.build_working_df(config)

    # Assert
    expected = pd.DataFrame([{"id": "1", "name": "Bob"}])
    pd.testing.assert_frame_equal(working_df, expected)


def test_commit_maps_deltas_onto_the_narrowed_slice(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the editor's row 0 is the slice's first row, not the table's
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="uuid-0", name="Alice"),
        _RowModel(id="uuid-1", name="Bob"),
    ]
    data_source = build_stub_data_source(rows=rows)
    config = _config(
        data_source=data_source,
        row_predicate=lambda row: row.name == "Bob",
    )
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert
    assert data_source.edits == [{"uuid-1": {"name": "Renamed"}}]


def test_commit_applies_editor_deltas_through_the_port(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="uuid-0", name="Alice"),
        _RowModel(id="uuid-1", name="Bob"),
    ]
    data_source = build_stub_data_source(rows=rows)
    config = _config(data_source=data_source)
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [1],
    }

    # Act
    grid.commit(config)

    # Assert - edits and deletions go through their own port methods
    assert all(
        [
            data_source.edits == [{"uuid-0": {"name": "Renamed"}}],
            data_source.deleted == ["uuid-1"],
        ],
    )


def test_commit_clears_the_widget_deltas(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [_RowModel(id="uuid-0", name="Alice")]
    config = _config(data_source=build_stub_data_source(rows=rows))
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert
    assert "test_table" not in st.session_state


def test_commit_skips_sample_data_without_crashing(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the port returns no rows, so the grid shows sample data (no id
    # column); editing it must not crash on the missing id when committing.
    sample = pd.DataFrame({"name": ["Example"]})
    data_source = build_stub_data_source(rows=[])
    config = _config(data_source=data_source, sample_data=sample)
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert - nothing written and the unpersistable deltas are cleared
    assert all(
        [
            data_source.edits == [],
            data_source.deleted == [],
            "test_table" not in st.session_state,
        ],
    )


def test_commit_is_a_noop_without_deltas(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    data_source = build_stub_data_source(rows=[_RowModel(id="uuid-0", name="Alice")])
    config = _config(data_source=data_source)
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert
    assert all([data_source.edits == [], data_source.deleted == []])
