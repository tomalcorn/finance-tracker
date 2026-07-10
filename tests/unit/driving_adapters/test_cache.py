"""Unit tests for the shared Streamlit cache mechanism."""

import streamlit as st

from driving_adapters import cache


class TestGetTableVersions:
    """Tests for the _get_table_versions function."""

    def test_creates_dict_in_session_state_if_missing(self) -> None:
        """Test that _get_table_versions creates the dict when not in session state."""
        result = cache._get_table_versions()
        assert all(
            [result == {}, cache._TABLE_VERSIONS_KEY in st.session_state],
        )

    def test_returns_existing_dict_from_session_state(self) -> None:
        """Test that _get_table_versions returns existing dict from session state."""
        st.session_state[cache._TABLE_VERSIONS_KEY] = {"users": 3}
        result = cache._get_table_versions()
        assert result == {"users": 3}

    def test_returns_same_reference(self) -> None:
        """Test that _get_table_versions returns a mutable reference."""
        versions = cache._get_table_versions()
        versions["test_table"] = expected_version = 5
        assert cache._get_table_versions()["test_table"] == expected_version
