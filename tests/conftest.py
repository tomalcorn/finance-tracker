"""Helper functions and fixtures for tests."""

import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from src.libs import config


def get_rendered_texts(app_tester: st_test.AppTest) -> list[str]:
    """Get all rendered texts from the app tester.

    Args:
        app_tester: The Streamlit app tester instance.

    Returns:
        A list of rendered texts.

    """
    texts = [t.value for t in getattr(app_tester, "text", [])]
    markdowns = [m.value for m in getattr(app_tester, "markdown", [])]
    return texts + markdowns


@pytest.fixture(name="col_configs")
def _col_configs() -> list[config.DFEColumnConfig]:
    return [
        config.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting=None,
        ),
    ]
