"""Unit tests for the pure grid_sync module (no Streamlit runtime needed)."""

from collections.abc import Callable

import pandas as pd
import pytest
import streamlit as st

from domain import query
from driving_adapters.components.dfes import grid_sync
from driving_adapters.models import frontend_models

ColumnConfigFactory = Callable[..., frontend_models.DFEColumnConfig]


@pytest.fixture(name="make_column_config")
def _make_column_config() -> ColumnConfigFactory:
    """Return a factory for minimal column configs carrying a filter or sort."""

    def _make(
        column_name: str,
        *,
        filters: query.Filters | None = None,
        sorting: query.SortingValues | None = None,
    ) -> frontend_models.DFEColumnConfig:
        return frontend_models.DFEColumnConfig(
            column_name=column_name,
            column_config={},
            input_widget=st.number_input,
            filters=filters,
            sorting=sorting,
        )

    return _make


class TestApplyActiveSorting:
    """Tests for apply_active_sorting."""

    def test_sorts_descending_by_configured_column(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A DESC sort config orders the frame high-to-low."""
        # Arrange
        df = pd.DataFrame({"payment_date": ["2026-01-01", "2026-03-01", "2026-02-01"]})
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(df, configs)

        # Assert
        expected = pd.DataFrame(
            {"payment_date": ["2026-03-01", "2026-02-01", "2026-01-01"]},
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_sorts_ascending_by_configured_column(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """An ASC sort config orders the frame low-to-high."""
        # Arrange
        df = pd.DataFrame({"payment_date": ["2026-03-01", "2026-01-01", "2026-02-01"]})
        configs = [make_column_config("payment_date", sorting=query.SortingValues.ASC)]

        # Act
        result = grid_sync.apply_active_sorting(df, configs)

        # Assert
        expected = pd.DataFrame(
            {"payment_date": ["2026-01-01", "2026-02-01", "2026-03-01"]},
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_returns_frame_unchanged_without_sort_config(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A frame is left untouched when no column declares a sort direction."""
        # Arrange
        df = pd.DataFrame({"payment_date": ["2026-03-01", "2026-01-01"]})
        configs = [make_column_config("payment_date", filters=query.Filters(eq="x"))]

        # Act
        result = grid_sync.apply_active_sorting(df, configs)

        # Assert
        pd.testing.assert_frame_equal(result, df)


class TestApplyColumnFilter:
    """Tests for apply_column_filter."""

    def test_eq_filter_on_string_column(self) -> None:
        """Equality filter keeps only matching rows."""
        df = pd.DataFrame({"payment_type": ["expense", "income", "expense"]})
        result = grid_sync.apply_column_filter(df, "payment_type", "==", "expense")
        assert list(result["payment_type"]) == ["expense", "expense"]

    def test_eq_filter_no_matches(self) -> None:
        """Equality filter returns empty when nothing matches."""
        df = pd.DataFrame({"payment_type": ["expense", "expense"]})
        result = grid_sync.apply_column_filter(df, "payment_type", "==", "income")
        assert result.empty

    def test_contains_filter(self) -> None:
        """Contains filter matches substrings."""
        df = pd.DataFrame({"name": ["test item", "other", "test thing"]})
        result = grid_sync.apply_column_filter(df, "name", "contains", "test")
        expected_count = 2
        assert len(result) == expected_count

    def test_gte_lte_filter_on_numeric(self) -> None:
        """>= and <= filters bound a numeric column."""
        df = pd.DataFrame({"value": [10, 20, 30, 40, 50]})
        result = grid_sync.apply_column_filter(df, "value", ">=", 20)
        result = grid_sync.apply_column_filter(result, "value", "<=", 40)
        assert list(result["value"]) == [20, 30, 40]

    def test_in_filter_on_scalar_column(self) -> None:
        """``in`` keeps rows whose scalar value is one of the selected values."""
        df = pd.DataFrame({"name": ["a", "b", "c"]})
        result = grid_sync.apply_column_filter(df, "name", "in", ["a", "c"])
        assert list(result["name"]) == ["a", "c"]

    def test_in_filter_on_list_column_matches_any_element(self) -> None:
        """``in`` keeps list-valued rows sharing any element with the selection."""
        df = pd.DataFrame({"budget_tracker_ids": [["a", "b"], ["c"], ["d", "e"]]})
        result = grid_sync.apply_column_filter(
            df,
            "budget_tracker_ids",
            "in",
            ["b", "d"],
        )
        assert list(result["budget_tracker_ids"]) == [["a", "b"], ["d", "e"]]


class TestPandasFilters:
    """Tests for pandas_filters operator translation."""

    def test_translates_comparison_operators(self) -> None:
        """gte/lte map to >=/<= and pass values through."""
        result = grid_sync.pandas_filters(query.Filters(gte=10, lte=100))
        assert result == {">=": 10, "<=": 100}

    def test_passes_through_non_comparison_keys(self) -> None:
        """Contains is kept verbatim, not remapped."""
        result = grid_sync.pandas_filters(query.Filters(contains="abc"))
        assert result == {"contains": "abc"}


class TestApplyActiveFilters:
    """Tests for apply_active_filters."""

    def test_applies_configured_filter(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A column config filter narrows the frame."""
        df = pd.DataFrame({"value": [10, 200, 30]})
        configs = [make_column_config("value", filters=query.Filters(lte=100))]
        result = grid_sync.apply_active_filters(df, configs)
        assert list(result["value"]) == [10, 30]

    def test_ignores_filter_for_absent_column(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A filter on a missing column is a no-op."""
        df = pd.DataFrame({"value": [10, 20]})
        configs = [make_column_config("missing", filters=query.Filters(lte=5))]
        result = grid_sync.apply_active_filters(df, configs)
        assert list(result["value"]) == [10, 20]


class TestEnforceUniqueCols:
    """Tests for the duplicate-name suffixing rule."""

    def test_no_duplicates(self) -> None:
        """A non-clashing value is left untouched."""
        row = {"name": "New Item", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Other Item", "Different Item"},
        )
        assert result == {"name": "New Item", "value": 100}

    def test_prefix_match_is_not_a_duplicate(self) -> None:
        """A prefix like Car must not collide with Carpet — only exact/suffixed."""
        row = {"name": "Car", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Carpet", "Cargo"},
        )
        assert result == {"name": "Car", "value": 100}

    def test_duplicate_without_suffix(self) -> None:
        """A bare duplicate gets a (1) suffix."""
        row = {"name": "Item", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Item", "Other Item"},
        )
        assert result == {"name": "Item (1)", "value": 100}

    def test_duplicate_with_suffix(self) -> None:
        """The next suffix is one past the current max."""
        row = {"name": "Item", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Item", "Item (1)", "Item (2)", "Other Item"},
        )
        assert result == {"name": "Item (3)", "value": 100}

    def test_row_value_already_suffixed(self) -> None:
        """An existing suffix on the row value is stripped before matching."""
        row = {"name": "Item (5)", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Item", "Item (1)", "Item (2)"},
        )
        assert result == {"name": "Item (3)", "value": 100}

    def test_column_not_in_row(self) -> None:
        """A unique column absent from the row is skipped (checker unused)."""
        row = {"value": 100}

        def _boom(_col: str) -> set[object]:
            msg = "checker should not be called"
            raise AssertionError(msg)

        result = grid_sync.enforce_unique_cols(row, ["name"], _boom)
        assert result == {"value": 100}

    def test_non_sequential_suffixes(self) -> None:
        """Gaps in suffix numbers still resolve to max + 1."""
        row = {"name": "Item", "value": 100}
        result = grid_sync.enforce_unique_cols(
            row,
            ["name"],
            lambda _col: {"Item", "Item (2)", "Item (5)", "Item (10)"},
        )
        assert result == {"name": "Item (11)", "value": 100}


class TestComputeBackendUpdates:
    """Tests for compute_backend_updates edit/delete diffing."""

    def test_edited_rows_keyed_by_id(self) -> None:
        """An edited row maps its backend id to the changes."""
        working_df = pd.DataFrame({"id": ["a", "b"], "total_budget": [10, 20]})
        updates = grid_sync.compute_backend_updates(
            working_df=working_df,
            edited_rows={"1": {"total_budget": 99}},
            deleted_rows=[],
            unique_col_names=[],
            unique_checker=lambda _col: set(),
        )
        assert updates.edited_rows == {"b": {"total_budget": 99}}
        assert updates.deleted_rows == []

    def test_deleted_rows_resolve_to_ids(self) -> None:
        """A deleted positional index resolves to its backend id."""
        working_df = pd.DataFrame({"id": ["a", "b", "c"]})
        updates = grid_sync.compute_backend_updates(
            working_df=working_df,
            edited_rows={},
            deleted_rows=[0, 2],
            unique_col_names=[],
            unique_checker=lambda _col: set(),
        )
        assert updates.deleted_rows == ["a", "c"]
        assert updates.edited_rows == {}

    def test_edit_applies_uniqueness_suffix(self) -> None:
        """An edit to a unique column is suffixed against existing values."""
        working_df = pd.DataFrame({"id": ["a"], "name": ["Item"]})
        updates = grid_sync.compute_backend_updates(
            working_df=working_df,
            edited_rows={"0": {"name": "Item"}},
            deleted_rows=[],
            unique_col_names=["name"],
            unique_checker=lambda _col: {"Item"},
        )
        assert updates.edited_rows == {"a": {"name": "Item (1)"}}
