"""Integration tests for the base_dfe module."""

from unittest import mock

import pandas as pd
import pydantic
import pytest
import streamlit as st

from libs import data_client, ss_keys
from libs.dfes import base_dfe
from libs.models import frontend_models


class _StubModel(pydantic.BaseModel):
    pass


@pytest.fixture(name="sample_df")
def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["id1", "id2", "id3"],
            "name": ["Item A", "Item B", "Item C"],
            "value": [100, 200, 300],
            "category": ["X", "Y", "Z"],
        },
    )


class TestDFESync:
    """Integration tests for the DFE.sync method."""

    def test_sync_with_edited_rows_no_unique_constraints(
        self,
        dfe_instance: base_dfe.DFE,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync method with edited rows and no unique constraints."""
        # Arrange
        dfe_instance.working_df = sample_df.copy()

        # Mock editor state with edited rows
        st.session_state[dfe_instance.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                0: {"value": 150},
                1: {"value": 250, "name": "Item B Updated"},
            },
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Act
        dfe_instance.sync()

        # Assert
        backend_updates = dfe_instance.backend_updates
        assert all(
            [
                backend_updates.added_rows == [],
                backend_updates.deleted_rows == [],
                backend_updates.edited_rows
                == {
                    "id1": {"value": 150},
                    "id2": {"value": 250, "name": "Item B Updated"},
                },
            ],
        )

    def test_sync_with_deleted_rows(
        self,
        dfe_instance: base_dfe.DFE,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync method with deleted rows."""
        # Arrange
        dfe_instance.working_df = sample_df.copy()

        # Mock editor state with deleted rows
        st.session_state[dfe_instance.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {},
            ss_keys.SSKeys.DELETED_ROWS: [0, 2],
        }

        # Act
        dfe_instance.sync()

        # Assert
        backend_updates = dfe_instance.backend_updates
        assert all(
            [
                backend_updates.added_rows == [],
                backend_updates.edited_rows == {},
                backend_updates.deleted_rows == ["id1", "id3"],
            ],
        )

    def test_sync_with_both_edited_and_deleted_rows(
        self,
        dfe_instance: base_dfe.DFE,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync method with both edited and deleted rows."""
        # Arrange
        dfe_instance.working_df = sample_df.copy()

        # Mock editor state
        st.session_state[dfe_instance.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                1: {"value": 250},
            },
            ss_keys.SSKeys.DELETED_ROWS: [0],
        }

        # Act
        dfe_instance.sync()

        # Assert
        backend_updates = dfe_instance.backend_updates
        assert all(
            [
                backend_updates.added_rows == [],
                backend_updates.edited_rows == {"id2": {"value": 250}},
                backend_updates.deleted_rows == ["id1"],
            ],
        )

    def test_sync_with_unique_column_no_duplicates(
        self,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync with unique column constraint when no duplicates exist."""
        # Arrange - create DFE with unique constraint on 'name'
        configs: list[frontend_models.DFEColumnConfigBase] = [
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config={},
                input_widget=st.text_input,
                enforce_unique=True,
            ),
        ]
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="test_table"
                ),
                backend_model=_StubModel,
                configs=configs,
                sample_data=pd.DataFrame(),
            ),
        )
        dfe.working_df = sample_df.copy()

        # Mock editor state
        st.session_state[dfe.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                0: {"name": "New Item"},
            },
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Mock get_column_values to return existing names
        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item B", "Item C", "Other Item"],
        ):
            # Act
            dfe.sync()

        # Assert - name should remain unchanged since no duplicates
        backend_updates = dfe.backend_updates
        assert backend_updates.edited_rows == {"id1": {"name": "New Item"}}

    def test_sync_with_unique_column_with_duplicates(
        self,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync with unique column constraint when duplicates exist."""
        # Arrange - create DFE with unique constraint on 'name'
        configs: list[frontend_models.DFEColumnConfigBase] = [
            frontend_models.DFEColumnConfig(
                column_name="name",
                column_config={},
                input_widget=st.text_input,
                enforce_unique=True,
            ),
        ]
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="test_table"
                ),
                backend_model=_StubModel,
                configs=configs,
                sample_data=pd.DataFrame(),
            ),
        )
        dfe.working_df = sample_df.copy()

        # Mock editor state
        st.session_state[dfe.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                0: {"name": "Item"},
            },
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Mock get_column_values to return duplicates
        with mock.patch.object(
            data_client,
            "get_column_values",
            return_value=["Item", "Item (1)", "Item (2)"],
        ):
            # Act
            dfe.sync()

        # Assert - name should be incremented to avoid duplicate
        backend_updates = dfe.backend_updates
        assert backend_updates.edited_rows == {"id1": {"name": "Item (3)"}}

    def test_sync_with_no_changes(
        self,
        dfe_instance: base_dfe.DFE,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync method when no changes are made."""
        # Arrange
        dfe_instance.working_df = sample_df.copy()

        # Mock editor state with no changes
        st.session_state[dfe_instance.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {},
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Act
        dfe_instance.sync()

        # Assert
        backend_updates = dfe_instance.backend_updates
        assert all(
            [
                backend_updates.added_rows == [],
                backend_updates.edited_rows == {},
                backend_updates.deleted_rows == [],
            ],
        )

    def test_sync_with_filters_changes_remain_in_filter(
        self,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync when edited rows remain within filter constraints."""
        # Arrange - create DFE with filter
        configs: list[frontend_models.DFEColumnConfigBase] = [
            frontend_models.DFEColumnConfig(
                column_name="value",
                column_config={},
                input_widget=st.number_input,
                filters=frontend_models.Filters(gte=100, lte=500),
            ),
        ]
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="test_table"
                ),
                backend_model=_StubModel,
                configs=configs,
                sample_data=pd.DataFrame(),
            ),
        )
        dfe.working_df = sample_df.copy()

        # Mock editor state - change value but keep within filter range
        st.session_state[dfe.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                0: {"value": 150},  # Changed from 100 to 150, still in range
            },
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Act
        dfe.sync()

        # Assert - working_df should remain 3 rows
        expected_length = 3
        backend_updates = dfe.backend_updates
        if dfe.working_df is None:
            msg = "working_df is None, expected filtered DataFrame"
            raise AssertionError(msg)
        assert all(
            [
                len(dfe.working_df) == expected_length,
                backend_updates.edited_rows == {"id1": {"value": 150}},
            ],
        )

    def test_sync_with_filters_changes_fall_outside_filter(
        self,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test sync when edited rows fall outside filter constraints."""
        # Arrange - create DFE with filter
        configs: list[frontend_models.DFEColumnConfigBase] = [
            frontend_models.DFEColumnConfig(
                column_name="value",
                column_config={},
                input_widget=st.number_input,
                filters=frontend_models.Filters(gte=100, lte=500),
            ),
        ]
        dfe = base_dfe.DFE(
            config=frontend_models.DFEConfig(
                table_names=frontend_models.DFETableNameConfig(
                    write_table="test_table"
                ),
                backend_model=_StubModel,
                configs=configs,
                sample_data=pd.DataFrame(),
            ),
        )
        dfe.working_df = sample_df.copy()

        # Mock editor state - change value outside filter range
        st.session_state[dfe.write_table] = {
            ss_keys.SSKeys.EDITED_ROWS: {
                0: {"value": 600},  # Changed from 100 to 600, outside range
            },
            ss_keys.SSKeys.DELETED_ROWS: [],
        }

        # Act
        dfe.sync()

        # Assert - working_df should be reduced to 2 rows (row 0 filtered out)
        expected_length = 2
        backend_updates = dfe.backend_updates
        if dfe.working_df is None:
            msg = "working_df is None, expected filtered DataFrame"
            raise AssertionError(msg)
        assert all(
            [
                len(dfe.working_df) == expected_length,
                "id1" not in dfe.working_df["id"].to_numpy(),
                backend_updates.edited_rows == {"id1": {"value": 600}},
            ],
        )
