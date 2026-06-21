"""Unit tests for the data client module."""

import streamlit as st

from domain import query
from ui import data_client
from ui.models import frontend_models


class TestGetTableVersions:
    """Tests for the _get_table_versions function."""

    def test_creates_dict_in_session_state_if_missing(self) -> None:
        """Test that _get_table_versions creates the dict when not in session state."""
        result = data_client._get_table_versions()
        assert all(
            [result == {}, data_client._TABLE_VERSIONS_KEY in st.session_state],
        )

    def test_returns_existing_dict_from_session_state(self) -> None:
        """Test that _get_table_versions returns existing dict from session state."""
        st.session_state[data_client._TABLE_VERSIONS_KEY] = {"users": 3}
        result = data_client._get_table_versions()
        assert result == {"users": 3}

    def test_returns_same_reference(self) -> None:
        """Test that _get_table_versions returns a mutable reference."""
        versions = data_client._get_table_versions()
        versions["test_table"] = expected_version = 5
        assert data_client._get_table_versions()["test_table"] == expected_version


class TestBuildFilterKey:
    """Tests for the _build_filter_key function."""

    def test_returns_empty_string_for_none(self) -> None:
        """Test that None configs return an empty string."""
        assert data_client._build_filter_key(None) == ""

    def test_returns_empty_string_for_empty_list(self) -> None:
        """Test that an empty list returns an empty string."""
        assert data_client._build_filter_key([]) == ""

    def test_includes_filter_info(self) -> None:
        """Test that filter info is included in the key."""
        configs = [
            frontend_models.DFEColumnConfigBase(
                column_name="payment_type",
                column_config={},
                input_widget=st.text_input,
                filters=query.Filters(eq="expense"),
            ),
        ]
        result = data_client._build_filter_key(configs)
        assert all(["payment_type" in result, "expense" in result])

    def test_includes_sorting_info(self) -> None:
        """Test that sorting info is included in the key."""
        configs = [
            frontend_models.DFEColumnConfigBase(
                column_name="date",
                column_config={},
                input_widget=st.text_input,
                sorting=query.SortingValues.DESC,
            ),
        ]
        result = data_client._build_filter_key(configs)
        assert "date:sort=desc" in result

    def test_different_filters_produce_different_keys(self) -> None:
        """Test that different filter configs produce different keys."""
        config_expense = [
            frontend_models.DFEColumnConfigBase(
                column_name="payment_type",
                column_config={},
                input_widget=st.text_input,
                filters=query.Filters(eq="expense"),
            ),
        ]
        config_income = [
            frontend_models.DFEColumnConfigBase(
                column_name="payment_type",
                column_config={},
                input_widget=st.text_input,
                filters=query.Filters(eq="income"),
            ),
        ]
        key_expense = data_client._build_filter_key(config_expense)
        key_income = data_client._build_filter_key(config_income)
        assert key_expense != key_income

    def test_skips_configs_without_filters_or_sorting(self) -> None:
        """Test that configs with no filters or sorting don't contribute to key."""
        configs = [
            frontend_models.DFEColumnConfigBase(
                column_name="name",
                column_config={},
                input_widget=st.text_input,
            ),
        ]
        assert data_client._build_filter_key(configs) == ""


