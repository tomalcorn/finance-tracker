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

    def test_oldest_row_leads_a_tie_by_default(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """Rows tied on the sorted column default to oldest-created first."""
        # Arrange
        rows = [
            {
                "id": "bbb",
                "payment_date": "2026-01-01",
                "created_at": "2026-01-01T10:00",
            },
            {
                "id": "aaa",
                "payment_date": "2026-01-01",
                "created_at": "2026-01-01T09:00",
            },
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(pd.DataFrame(rows), configs)

        # Assert
        assert result["id"].tolist() == ["aaa", "bbb"]

    def test_newest_row_leads_a_tie_when_insertion_sorting_is_desc(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A DESC insertion sorting puts the newest-created row atop its tie."""
        # Arrange
        rows = [
            {
                "id": "aaa",
                "payment_date": "2026-01-01",
                "created_at": "2026-01-01T09:00",
            },
            {
                "id": "bbb",
                "payment_date": "2026-01-01",
                "created_at": "2026-01-01T10:00",
            },
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(
            pd.DataFrame(rows),
            configs,
            query.SortingValues.DESC,
        )

        # Assert
        assert result["id"].tolist() == ["bbb", "aaa"]

    def test_insertion_sorting_never_reorders_distinct_sort_values(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """The configured sort still wins: the tiebreak only orders ties."""
        # Arrange - the newest row is the one with the oldest payment date
        rows = [
            {
                "id": "aaa",
                "payment_date": "2026-01-01",
                "created_at": "2026-01-02T09:00",
            },
            {
                "id": "bbb",
                "payment_date": "2026-03-01",
                "created_at": "2026-01-01T09:00",
            },
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(
            pd.DataFrame(rows),
            configs,
            query.SortingValues.DESC,
        )

        # Assert
        assert result["payment_date"].tolist() == ["2026-03-01", "2026-01-01"]

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


class TestSortingIsIndependentOfFetchOrder:
    """The editor maps its deltas by position, so order must not drift (#236).

    A delta is recorded against a row index on one run and resolved against a
    frame rebuilt on the next. If the same rows can come back in a different
    order, an edit or a deletion lands on the wrong row.
    """

    def test_rows_tied_on_the_sorted_column_keep_one_order(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """Two fetches of the same tied rows sort into the same order."""
        # Arrange - identical rows, opposite arrival order, tied on the sort key
        rows = [
            {"id": "aaa", "payment_date": "2026-01-01"},
            {"id": "bbb", "payment_date": "2026-01-01"},
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        first = grid_sync.apply_active_sorting(pd.DataFrame(rows), configs)
        second = grid_sync.apply_active_sorting(
            pd.DataFrame(list(reversed(rows))),
            configs,
        )

        # Assert
        pd.testing.assert_frame_equal(first, second)

    def test_an_unsorted_frame_is_ordered_too(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """A grid with no sort config is still not left in fetch order."""
        # Arrange - no column declares a sort, so today's order is the fetch's
        rows = [{"id": "aaa", "name": "One"}, {"id": "bbb", "name": "Two"}]
        configs = [make_column_config("name")]

        # Act
        first = grid_sync.apply_active_sorting(pd.DataFrame(rows), configs)
        second = grid_sync.apply_active_sorting(
            pd.DataFrame(list(reversed(rows))),
            configs,
        )

        # Assert
        pd.testing.assert_frame_equal(first, second)

    def test_rows_tied_on_creation_keep_one_order_under_desc_insertion(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """The id key still settles rows a DESC insertion sorting leaves tied."""
        # Arrange - identical rows, opposite arrival order, tied on both keys
        rows = [
            {"id": "aaa", "created_at": "2026-01-01T09:00"},
            {"id": "bbb", "created_at": "2026-01-01T09:00"},
        ]
        configs = [make_column_config("created_at")]

        # Act
        first = grid_sync.apply_active_sorting(
            pd.DataFrame(rows),
            configs,
            query.SortingValues.DESC,
        )
        second = grid_sync.apply_active_sorting(
            pd.DataFrame(list(reversed(rows))),
            configs,
            query.SortingValues.DESC,
        )

        # Assert
        pd.testing.assert_frame_equal(first, second)

    def test_the_configured_sort_still_wins_over_the_tiebreak(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """The tiebreak orders ties only; it never reorders distinct values."""
        # Arrange - the id order is the opposite of the wanted date order
        rows = [
            {"id": "aaa", "payment_date": "2026-01-01"},
            {"id": "bbb", "payment_date": "2026-03-01"},
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(pd.DataFrame(rows), configs)

        # Assert
        assert result["payment_date"].tolist() == ["2026-03-01", "2026-01-01"]

    def test_ties_are_broken_by_insertion_order_not_by_id(
        self,
        make_column_config: ColumnConfigFactory,
    ) -> None:
        """Tied rows read oldest-first, which id order alone would not give."""
        # Arrange - the id order is deliberately the reverse of the created order
        rows = [
            {
                "id": "zzz",
                "created_at": "2026-01-01T00:00:00Z",
                "payment_date": "2026-01-01",
            },
            {
                "id": "aaa",
                "created_at": "2026-02-01T00:00:00Z",
                "payment_date": "2026-01-01",
            },
        ]
        configs = [make_column_config("payment_date", sorting=query.SortingValues.DESC)]

        # Act
        result = grid_sync.apply_active_sorting(pd.DataFrame(rows), configs)

        # Assert
        assert result["id"].tolist() == ["zzz", "aaa"]


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


class TestComputeDeltas:
    """Tests for compute_deltas edit/delete diffing."""

    def test_edited_rows_keyed_by_id(self) -> None:
        """An edited row maps its backend id to the changes."""
        working_df = pd.DataFrame({"id": ["a", "b"], "total_budget": [10, 20]})
        edits, deleted_ids = grid_sync.compute_deltas(
            working_df=working_df,
            edited_rows={"1": {"total_budget": 99}},
            deleted_rows=[],
            unique_col_names=[],
            unique_checker=lambda _col: set(),
        )
        assert all([edits == {"b": {"total_budget": 99}}, deleted_ids == []])

    def test_deleted_rows_resolve_to_ids(self) -> None:
        """A deleted positional index resolves to its backend id."""
        working_df = pd.DataFrame({"id": ["a", "b", "c"]})
        edits, deleted_ids = grid_sync.compute_deltas(
            working_df=working_df,
            edited_rows={},
            deleted_rows=[0, 2],
            unique_col_names=[],
            unique_checker=lambda _col: set(),
        )
        assert all([deleted_ids == ["a", "c"], edits == {}])

    def test_edit_applies_uniqueness_suffix(self) -> None:
        """An edit to a unique column is suffixed against existing values."""
        working_df = pd.DataFrame({"id": ["a"], "name": ["Item"]})
        edits, _ = grid_sync.compute_deltas(
            working_df=working_df,
            edited_rows={"0": {"name": "Item"}},
            deleted_rows=[],
            unique_col_names=["name"],
            unique_checker=lambda _col: {"Item"},
        )
        assert edits == {"a": {"name": "Item (1)"}}
