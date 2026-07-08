"""Unit tests for the Supabase client module."""

from unittest import mock

from driven_adapters.supabase import client
from driving_adapters.models import frontend_models


def test_apply_filters_to_query(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test applying filters to a query."""
    mock_query = mock.Mock()

    client._apply_filters_to_query(
        mock_query,
        col_configs[0].column_name,
        col_configs[0].filters,
    )

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
    mock_query = mock.Mock()

    client._apply_sorting_to_query(
        mock_query,
        col_configs[0].column_name,
        col_configs[0].sorting,
    )

    mock_query.order.assert_called_once_with(
        "col1",
        desc=False,
    )
