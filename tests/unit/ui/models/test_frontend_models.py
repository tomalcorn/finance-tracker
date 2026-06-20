"""Unit tests for the frontend models module."""

import pytest
from ui.models import frontend_models


class TestFilters:
    """Tests for the Filters model."""

    @pytest.mark.parametrize(
        ("filters_kwargs", "expected"),
        [
            pytest.param({"eq": "expense"}, {"==": "expense"}, id="eq"),
            pytest.param({"gte": 10, "lte": 100}, {">=": 10, "<=": 100}, id="range"),
            pytest.param({"lt": 5, "gt": 1}, {"<": 5, ">": 1}, id="lt_gt"),
            pytest.param({"contains": "test"}, {"contains": "test"}, id="contains"),
            pytest.param({}, {}, id="empty"),
        ],
    )
    def test_get_pandas_filters(
        self,
        filters_kwargs: dict,
        expected: dict,
    ) -> None:
        """Test that get_pandas_filters maps operators correctly."""
        filters = frontend_models.Filters(**filters_kwargs)
        assert filters.get_pandas_filters() == expected


class TestDFEColumnConfig:
    """Tests for the DFEColumnConfig data model."""

    @pytest.mark.parametrize(
        "value",
        ["asc", "desc", None],
    )
    def test_validate_sorting_with_valid_values(self, value: str | None) -> None:
        """Test validate_sorting with valid sorting values."""
        result = frontend_models.DFEColumnConfig.validate_sorting(value)
        assert result == value

    def test_validate_sorting_with_invalid_value(self) -> None:
        """Test validate_sorting raises ValueError with invalid sorting value."""
        invalid_value = "invalid_sort"
        with pytest.raises(
            ValueError,
            match=f"Invalid sorting value: {invalid_value}.",
        ):
            frontend_models.DFEColumnConfig.validate_sorting(invalid_value)
