"""Unit tests for the config module."""

import pytest
from src.libs import config


class TestDFEColumnConfig:
    """Tests for the DFEColumnConfig data model."""

    @pytest.mark.parametrize(
        "value",
        ["asc", "desc", None],
    )
    def test_validate_sorting_with_valid_values(self, value: str | None) -> None:
        """Test validate_sorting with valid sorting values."""
        result = config.DFEColumnConfig.validate_sorting(value)
        assert result == value

    def test_validate_sorting_with_invalid_value(self) -> None:
        """Test validate_sorting raises ValueError with invalid sorting value."""
        invalid_value = "invalid_sort"
        with pytest.raises(
            ValueError,
            match=f"Invalid sorting value: {invalid_value}.",
        ):
            config.DFEColumnConfig.validate_sorting(invalid_value)
