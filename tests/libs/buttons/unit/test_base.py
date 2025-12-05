"""Tests for the BaseButton class."""

import streamlit as st

from libs import constants, frontend_models
from libs.buttons import base


def test_override_configs_from_session_state_returns_none(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test _override_configs_from_session_state returns None when no session state."""
    # Arrange
    base_button = base.BaseButton("test_table", col_configs)

    # Act
    result = base_button._override_configs_from_session_state()

    # Assert
    assert result is None


def test_override_configs_from_session_state_returns_configs(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test _override_configs_from_session_state returns configs from session state."""
    # Arrange
    base_button = base.BaseButton("test_table", [])

    # Set session state
    session_key = f"test_table_{constants.SSKeys.COL_CONFIGS}"
    st.session_state[session_key] = col_configs

    # Act
    result = base_button._override_configs_from_session_state()

    # Assert
    assert result == col_configs
