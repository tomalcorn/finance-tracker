"""Unit tests for the pure grid_sync module (no Streamlit runtime needed)."""

import pandas as pd
import streamlit as st

from domain import query
from ui.components.dfes import grid_sync
from ui.models import frontend_models


def _config(
    column_name: str,
    filters: query.Filters,
) -> frontend_models.DFEColumnConfigBase:
    """Build a minimal column config carrying a filter."""
    return frontend_models.DFEColumnConfigBase(
        column_name=column_name,
        column_config={},
        input_widget=st.number_input,
        filters=filters,
    )


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

    def test_applies_configured_filter(self) -> None:
        """A column config filter narrows the frame."""
        df = pd.DataFrame({"value": [10, 200, 30]})
        configs = [_config("value", query.Filters(lte=100))]
        result = grid_sync.apply_active_filters(df, configs)
        assert list(result["value"]) == [10, 30]

    def test_ignores_filter_for_absent_column(self) -> None:
        """A filter on a missing column is a no-op."""
        df = pd.DataFrame({"value": [10, 20]})
        configs = [_config("missing", query.Filters(lte=5))]
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


class TestCheckForFiltersUpdates:
    """Tests for re-applying filters after edits."""

    def test_edit_pushes_row_out_of_range(self) -> None:
        """An edit beyond the active filter drops the row and flags a change."""
        working_df = pd.DataFrame({"id": ["a", "b"], "value": [10, 20]})
        configs = [_config("value", query.Filters(lte=100))]
        changed, modified = grid_sync.check_for_filters_updates(
            working_df=working_df,
            edited_rows={"0": {"value": 999}},
            deleted_rows=[],
            active_configs=configs,
        )
        assert changed is True
        assert list(modified["value"]) == [20]

    def test_no_change_when_edit_stays_in_range(self) -> None:
        """An in-range edit keeps every row and flags no change."""
        working_df = pd.DataFrame({"id": ["a", "b"], "value": [10, 20]})
        configs = [_config("value", query.Filters(lte=100))]
        changed, modified = grid_sync.check_for_filters_updates(
            working_df=working_df,
            edited_rows={"0": {"value": 50}},
            deleted_rows=[],
            active_configs=configs,
        )
        assert changed is False
        assert len(modified) == len(working_df)

    def test_delete_shrinks_frame(self) -> None:
        """A delete removes the row and flags a change."""
        working_df = pd.DataFrame({"id": ["a", "b"], "value": [10, 20]})
        changed, modified = grid_sync.check_for_filters_updates(
            working_df=working_df,
            edited_rows={},
            deleted_rows=[0],
            active_configs=[],
        )
        assert changed is True
        assert list(modified["value"]) == [20]
