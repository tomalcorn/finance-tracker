"""Unit tests for the Streamlit cache implementation."""

import pytest
import streamlit as st

from driving_adapters import cache


@pytest.fixture(autouse=True)
def _clear_data_cache() -> None:
    """Reset the module-global cache stores between tests."""
    cache._get_data_cached.clear()
    cache._key_versions.clear()


class TestGetKeyVersions:
    """Tests for the _get_key_versions function."""

    def test_starts_empty(self) -> None:
        # Act
        result = cache._get_key_versions()

        # Assert
        assert result == {}

    def test_returns_same_reference(self) -> None:
        # Arrange
        versions = cache._get_key_versions()
        versions["test_key"] = expected_version = 5

        # Act / Assert - a later lookup sees the mutation
        assert cache._get_key_versions()["test_key"] == expected_version

    def test_versions_are_not_stored_in_session_state(self) -> None:
        # Arrange - a fresh session starts with empty session state; the
        # version map must live outside it so invalidations survive a reload.
        key = "auth0|user:budget_tracker_view"
        cache.StreamlitCache().invalidate([key])

        # Act - simulate a brand-new session by wiping session state
        st.session_state.clear()

        # Assert - the bump is still visible (it never lived in session state)
        assert cache._get_key_versions().get(key) == 1


class TestGetOrLoad:
    """Tests for StreamlitCache.get_from_or_load_cache."""

    def test_runs_the_loader_on_a_cold_key(self) -> None:
        # Arrange
        rows: list[dict[str, object]] = [{"id": "1"}]

        # Act
        result = cache.StreamlitCache().get_from_or_load_cache(
            "user|a:payments",
            lambda: rows,
        )

        # Assert
        assert result == rows

    def test_serves_a_warm_key_without_rerunning_the_loader(self) -> None:
        # Arrange - warm the cache for a key, then a loader that records calls
        key = "user|a:bank_accounts"
        warm: list[dict[str, object]] = [{"n": 1}]
        cache.StreamlitCache().get_from_or_load_cache(key, lambda: warm)
        calls: list[int] = []

        def _loader() -> list[dict[str, object]]:
            calls.append(1)
            return [{"n": 2}]

        # Act - same (key, version) → cache hit
        result = cache.StreamlitCache().get_from_or_load_cache(key, _loader)

        # Assert - first value served, loader never called
        assert all([result == warm, calls == []])

    def test_a_bumped_version_reruns_the_loader(self) -> None:
        # Arrange
        key = "user|a:one_offs"
        old: list[dict[str, object]] = [{"v": "old"}]
        new: list[dict[str, object]] = [{"v": "new"}]
        cache.StreamlitCache().get_from_or_load_cache(key, lambda: old)

        # Act - invalidate bumps the version, missing the cache
        cache.StreamlitCache().invalidate([key])
        result = cache.StreamlitCache().get_from_or_load_cache(key, lambda: new)

        # Assert
        assert result == new


class TestInvalidate:
    """Tests for StreamlitCache.invalidate."""

    def test_bumps_the_version_of_each_given_key(self) -> None:
        # Act
        cache.StreamlitCache().invalidate(["k1", "k2"])

        # Assert
        versions = cache._get_key_versions()
        assert all([versions["k1"] == 1, versions["k2"] == 1])

    def test_leaves_unmentioned_keys_untouched(self) -> None:
        # Arrange
        untouched_version = 7
        cache._get_key_versions()["other"] = untouched_version

        # Act
        cache.StreamlitCache().invalidate(["k1"])

        # Assert
        assert cache._get_key_versions()["other"] == untouched_version
