"""Module for the BaseButton class."""

import streamlit as st

from libs import constants, frontend_models


class BaseButton:
    """Base class for buttons."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[frontend_models.DFEColumnConfig],
    ) -> None:
        """Initialize the BaseButton instance."""
        self._table_name = table_name
        self._col_configs = col_configs
        self.css_style_normal = """
            button {
                background-color: white;
                border: 1px solid #ccc;
                color: black;
            }
            """
        self.css_style_active = """
            button {
            background-color: rgba(212, 237, 218, 0.5); /* Light green background */
            border: 1px solid #ccc;
            color: black;
            }
            """

    def _override_configs_from_session_state(
        self,
    ) -> list[frontend_models.DFEColumnConfig] | None:
        """Override column configs from session state if available."""
        session_key = f"{self._table_name}_{constants.SSKeys.COL_CONFIGS}"
        if session_key in st.session_state:
            configs: list[frontend_models.DFEColumnConfig] = st.session_state[
                session_key
            ]
            return configs
        return None
