"""Unit tests for the frontend models module."""

import pandas as pd
import pydantic
import pytest
from driving_adapters.models import frontend_models

from domain import entities


class _StubModel(pydantic.BaseModel):
    pass


class _StubDataSource:
    """Minimal GridDataSource for DFEConfig validation tests."""

    def rows(self) -> list[pydantic.BaseModel]:
        return []

    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return set()

    def apply(self, changes: entities.BackendUpdates) -> None:
        """Record nothing; DFEConfig validation never writes."""


class TestDFEConfig:
    """Tests for the DFEConfig data model."""

    def test_read_via_repository_without_data_source_raises(self) -> None:
        """read_via_repository=True without a data_source is rejected."""
        with pytest.raises(
            pydantic.ValidationError,
            match=r"read_via_repository=True requires a data_source\.",
        ):
            frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(write_table="users"),
                backend_model=_StubModel,
                configs=[],
                sample_data=pd.DataFrame(),
                read_via_repository=True,
            )

    def test_read_via_repository_with_data_source_is_valid(self) -> None:
        """read_via_repository=True with a data_source is accepted."""
        config = frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(write_table="users"),
            backend_model=_StubModel,
            configs=[],
            sample_data=pd.DataFrame(),
            read_via_repository=True,
            data_source=_StubDataSource(),
        )
        assert config.read_via_repository is True

    def test_no_repository_read_without_data_source_is_valid(self) -> None:
        """The legacy path (no repository read, no data_source) stays valid."""
        config = frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(write_table="users"),
            backend_model=_StubModel,
            configs=[],
            sample_data=pd.DataFrame(),
        )
        assert all([config.read_via_repository is False, config.data_source is None])
