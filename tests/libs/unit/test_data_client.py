"""Unit tests for the data client module."""

from unittest import mock

import pandas as pd

from libs import data_client, frontend_models


def test_apply_filters_to_query(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test applying filters to a query."""
    # Arrange
    with mock.patch("libs.data_client.st_supabase_connection") as mock_st_supabase:
        mock_query = mock.Mock()
        mock_st_supabase.SyncSelectRequestBuilder.return_value = mock_query

        data_client._apply_filters_to_query(mock_query, col_configs[0])

        # Assert
        assert all(
            [
                mock_query.filter.mock_calls[0][1][1] == "lte",
                mock_query.filter.mock_calls[0][1][2] == "2023-01-01",
                mock_query.filter.mock_calls[1][1][1] == "gte",
                mock_query.filter.mock_calls[1][1][2] == "2022-01-01",
            ],
        )


def test_apply_sorting_to_query(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test applying sorting to a query."""
    # Arrange
    with mock.patch("libs.data_client.st_supabase_connection") as mock_st_supabase:
        mock_query = mock.Mock()
        mock_st_supabase.SyncSelectRequestBuilder.return_value = mock_query

        data_client._apply_sorting_to_query(mock_query, col_configs[0])

        # Assert
        mock_query.order.assert_called_once_with(
            "col1",
            desc=False,
        )


def test_update_backend_returns_updated_backend_updates() -> None:
    """Test that update_backend returns the updated backend updates."""
    # Arrange
    current_df = pd.DataFrame({"id": [1, 2, 3], "col1": ["a", "b", "c"]})
    modified_df = pd.DataFrame({"id": [2, 3, 4], "col1": ["b", "c", "d"]})

    backend_updates = frontend_models.BackendUpdates(
        added_rows=[{"col1": "value1"}],
        edited_rows={"1": {"col1": "new_value"}},
        deleted_rows=[{"col2": "value2"}],
        row_ids=["1", "2"],
        prev_added_rows=[{"col1": "value1"}],
    )

    with mock.patch("libs.data_client.CONN") as mock_conn:
        mock_table = mock.Mock()
        mock_conn.table.return_value = mock_table

        mock_insert = mock.Mock()
        mock_insert.execute.return_value = None
        mock_table.insert.return_value = mock_insert

        mock_update = mock.Mock()
        mock_eq = mock.Mock()
        mock_eq.execute.return_value = None
        mock_update.eq.return_value = mock_eq
        mock_table.update.return_value = mock_update

        mock_delete = mock.Mock()
        mock_in = mock.Mock()
        mock_in.execute.return_value = None
        mock_delete.in_.return_value = mock_in
        mock_table.delete.return_value = mock_delete

        # Act
        updated_backend_updates = data_client.update_backend(
            table_name="test_table",
            updates=backend_updates,
            current_df=current_df,
            modified_df=modified_df,
        )

        # Assert
        expected_updated_backend_updates = frontend_models.BackendUpdates(
            added_rows=[{"col1": "value1"}],
            edited_rows={"1": {"col1": "new_value"}},
            deleted_rows=[],
            row_ids=["1", "2"],
            prev_added_rows=[{"col1": "value1"}],
        )

        assert updated_backend_updates == expected_updated_backend_updates
