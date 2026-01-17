"""Unit tests for the data client module."""

from unittest import mock

from apps import data_client
from libs import frontend_models


def test_apply_filters_to_query(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test applying filters to a query."""
    # Arrange
    with mock.patch("apps.data_client.st_supabase_connection") as mock_st_supabase:
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
    with mock.patch("apps.data_client.st_supabase_connection") as mock_st_supabase:
        mock_query = mock.Mock()
        mock_st_supabase.SyncSelectRequestBuilder.return_value = mock_query

        data_client._apply_sorting_to_query(mock_query, col_configs[0])

        # Assert
        mock_query.order.assert_called_once_with(
            "col1",
            desc=False,
        )
