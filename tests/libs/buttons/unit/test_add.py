"""Unit tests for the add module."""

import pytest
import streamlit.testing.v1 as st_test
from tests import conftest


def _add_button_dialog_wrapper() -> None:
    """Call the _add_button_dialog method."""
    import streamlit as st  # noqa: F401 - needed for app_test from_function

    from libs.buttons import add

    add_button = add.AddButton("test_table", [])

    return add_button._add_button_dialog()


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _add_button_dialog_wrapper,
        default_timeout=120,
    )


class TestAddButton:
    """Tests for the AddButton class."""

    def test_add_button_dialog(self, app_tester: st_test.AppTest) -> None:
        """Test the _add_button_dialog method."""
        # Act - render button
        app_tester.run()

        # Assert - submit button and dialog text present
        submit_button_key_rendered = any(
            btn.key == "test_table_submit_new_row_button" for btn in app_tester.button
        )
        submit_button_label_rendered = any(
            btn.label == "Submit" for btn in app_tester.button
        )
        dialog_text_rendered = (
            "Add a new row to test_table" in conftest.get_rendered_texts(app_tester)
        )
        assert all(
            [
                submit_button_key_rendered,
                submit_button_label_rendered,
                dialog_text_rendered,
            ],
        )
