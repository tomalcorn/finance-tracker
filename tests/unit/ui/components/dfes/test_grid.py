"""Unit tests for the grid free functions (build_working_df + commit)."""

import pandas as pd
import pydantic
import streamlit as st

from domain import entities
from ui import ss_keys
from ui.components.dfes import grid
from ui.models import frontend_models


class _StubModel(pydantic.BaseModel):
    pass


class _RowModel(pydantic.BaseModel):
    id: str
    name: str


class _StubDataSource:
    """GridDataSource stub: fixed rows/column values, records applied batches."""

    def __init__(
        self,
        rows: list[pydantic.BaseModel] | None = None,
        column_values: set[object] | None = None,
    ) -> None:
        self._rows = rows or []
        self._column_values = column_values or set()
        self.applied: list[entities.BackendUpdates] = []

    def rows(self) -> list[pydantic.BaseModel]:
        return self._rows

    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return self._column_values

    def apply(self, changes: entities.BackendUpdates) -> None:
        self.applied.append(changes)


def _config(
    *,
    data_source: _StubDataSource | None = None,
    sample_data: pd.DataFrame | None = None,
) -> frontend_models.DFEConfig:
    """Build a minimal grid config for the tests."""
    return frontend_models.DFEConfig(
        table_names=frontend_models.DFETableNameConfig(write_table="test_table"),
        backend_model=_StubModel,
        configs=[],
        sample_data=pd.DataFrame() if sample_data is None else sample_data,
        data_source=data_source,
        read_via_repository=data_source is not None,
    )


def test_build_working_df_reads_from_data_source() -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="0", name="Alice"),
        _RowModel(id="1", name="Bob"),
    ]
    config = _config(data_source=_StubDataSource(rows=rows))

    # Act
    working_df = grid.build_working_df(config)

    # Assert
    expected = pd.DataFrame([{"id": "0", "name": "Alice"}, {"id": "1", "name": "Bob"}])
    pd.testing.assert_frame_equal(working_df, expected)


def test_build_working_df_falls_back_to_sample_when_source_empty() -> None:
    # Arrange
    sample = pd.DataFrame({"name": ["Example"]})
    config = _config(data_source=_StubDataSource(rows=[]), sample_data=sample)

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


def test_commit_applies_editor_deltas_through_the_port() -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [
        _RowModel(id="uuid-0", name="Alice"),
        _RowModel(id="uuid-1", name="Bob"),
    ]
    data_source = _StubDataSource(rows=rows)
    config = _config(data_source=data_source)
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [1],
    }

    # Act
    grid.commit(config)

    # Assert
    assert data_source.applied == [
        entities.BackendUpdates(
            edited_rows={"uuid-0": {"name": "Renamed"}},
            deleted_rows=["uuid-1"],
        ),
    ]


def test_commit_clears_the_widget_deltas() -> None:
    # Arrange
    rows: list[pydantic.BaseModel] = [_RowModel(id="uuid-0", name="Alice")]
    config = _config(data_source=_StubDataSource(rows=rows))
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {"0": {"name": "Renamed"}},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert
    assert "test_table" not in st.session_state


def test_commit_is_a_noop_without_deltas() -> None:
    # Arrange
    data_source = _StubDataSource(rows=[_RowModel(id="uuid-0", name="Alice")])
    config = _config(data_source=data_source)
    st.session_state["test_table"] = {
        ss_keys.SSKeys.EDITED_ROWS: {},
        ss_keys.SSKeys.DELETED_ROWS: [],
    }

    # Act
    grid.commit(config)

    # Assert
    assert data_source.applied == []
