"""Unit tests for the cache module."""

import pytest
from libs.caching import cache


class TestCacheDecorator:
    """Tests for the cache decorator."""

    def test_same_args_return_cached_result(self) -> None:
        """Function is only called once for the same arguments."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        result1 = my_func("x", 1)
        result2 = my_func("x", 1)

        # Assert
        assert all([result1 == "x-1", result2 == "x-1", call_count == 1])

    def test_different_args_produce_separate_cache_entries(self) -> None:
        """Different arguments produce separate cache entries."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        result1 = my_func("x", 1)
        result2 = my_func("x", 2)

        # Assert
        expected_call_count = 2
        assert all(
            [result1 == "x-1", result2 == "x-2", call_count == expected_call_count],
        )

    def test_clear_no_args_flushes_entire_cache(self) -> None:
        """clear() with no arguments removes all cached entries."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str) -> str:
            nonlocal call_count
            call_count += 1
            return a

        # Act
        my_func("x")
        my_func("y")
        my_func.clear()
        my_func("x")  # cache miss — should re-execute

        # Assert
        expected_call_count = 3
        assert call_count == expected_call_count

    def test_clear_kwarg_removes_all_matching_entries(self) -> None:
        """clear(a='x') removes all entries where a=='x', regardless of b."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        my_func("x", 1)
        my_func("x", 2)
        my_func("y", 1)
        my_func.clear(a="x")
        my_func("x", 1)  # cache miss
        my_func("x", 2)  # cache miss
        my_func("y", 1)  # still cached

        # Assert
        expected_call_count = 5
        assert call_count == expected_call_count

    def test_clear_kwarg_leaves_unmatched_entries_intact(self) -> None:
        """clear(a='x') does not remove entries where a!='x'."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        my_func("x", 1)
        my_func("y", 1)
        my_func.clear(a="x")
        my_func("y", 1)  # should still be cached

        # Assert
        expected_call_count = 2
        assert call_count == expected_call_count

    def test_clear_multiple_kwargs_must_all_match(self) -> None:
        """clear(a='x', b=1) only removes the entry where both conditions hold."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        my_func("x", 1)
        my_func("x", 2)
        my_func.clear(a="x", b=1)
        my_func("x", 1)  # cache miss
        my_func("x", 2)  # still cached

        # Assert
        expected_call_count = 3
        assert call_count == expected_call_count

    def test_clear_invalid_kwarg_raises_value_error(self) -> None:
        """Passing an unknown parameter name to clear() raises ValueError."""

        # Arrange
        @cache
        def my_func(a: str) -> str:
            return a

        # Act / Assert
        with pytest.raises(ValueError, match="not a cacheable parameter"):
            my_func.clear(nonexistent="value")

    def test_underscore_prefix_excluded_from_cache_key(self) -> None:
        """Parameters prefixed with '_' do not affect the cache key."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, _conn: object | None = None) -> str:
            nonlocal call_count
            call_count += 1
            return a

        # Act
        my_func("x", _conn=object())
        my_func("x", _conn=object())  # different _conn — same cache key

        # Assert
        assert call_count == 1

    def test_underscore_params_not_clearable(self) -> None:
        """Underscore-prefixed parameters are not accepted by clear()."""

        # Arrange
        @cache
        def my_func(a: str, _conn: object | None = None) -> str:
            return a

        # Act / Assert
        with pytest.raises(ValueError, match="not a cacheable parameter"):
            my_func.clear(_conn=object())

    def test_list_args_are_handled_correctly(self) -> None:
        """List arguments are converted to a hashable form for caching."""
        # Arrange
        call_count = 0

        @cache
        def my_func(items: list[str]) -> int:
            nonlocal call_count
            call_count += 1
            return len(items)

        # Act
        my_func(["a", "b"])
        my_func(["a", "b"])

        # Assert
        assert call_count == 1

    def test_different_list_args_produce_separate_entries(self) -> None:
        """Different list values produce separate cache entries."""

        # Arrange
        @cache
        def my_func(items: list[str]) -> list[str]:
            return items[:]

        # Act
        result1 = my_func(["a"])
        result2 = my_func(["b"])

        # Assert
        assert all([result1 == ["a"], result2 == ["b"]])

    def test_default_args_and_explicit_args_share_cache_entry(self) -> None:
        """Explicit call with default value hits the same entry as omitting it."""
        # Arrange
        call_count = 0

        @cache
        def my_func(a: str, b: int = 42) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}-{b}"

        # Act
        my_func("x")
        my_func("x", 42)  # same effective arguments

        # Assert
        assert call_count == 1
