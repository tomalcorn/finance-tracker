"""Unit tests for the add button module."""

import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from tests import conftest

from apps.buttons import add_button
from libs.models import frontend_models


def _add_button_dialog_wrapper() -> None:
    """Call the _add_button_dialog method."""
    import streamlit as st  # noqa: F401 - needed for app_test from_function

    from apps.buttons import add_button
    from libs.models import backend_models

    add_button_instance = add_button.AddButton(
        "test_table",
        backend_model=backend_models.UserModel,
    )

    return add_button_instance._add_button_dialog([])


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
            "Add a new row to Test Table" in conftest.get_rendered_texts(app_tester)
        )
        assert all(
            [
                submit_button_key_rendered,
                submit_button_label_rendered,
                dialog_text_rendered,
            ],
        )


def _make_col_config(
    name: str,
    *,
    required: bool = True,
) -> frontend_models.DFEColumnConfig:
    return frontend_models.DFEColumnConfig(
        column_name=name,
        column_config=st.column_config.TextColumn(name),
        button_label=name,
        input_widget=st.text_input,
        input_kwargs={},
        required=required,
    )


def _req(name: str = "name") -> frontend_models.DFEColumnConfig:
    return _make_col_config(name, required=True)


def _opt(name: str = "end_date") -> frontend_models.DFEColumnConfig:
    return _make_col_config(name, required=False)


class TestAddButtonRequiredField:
    """Tests for the required field behaviour on the add button."""

    @pytest.mark.parametrize(
        ("col_configs", "outputs", "expected"),
        [
            pytest.param([_req()], [""], True, id="required_empty"),
            pytest.param([_req()], [None], True, id="required_none"),
            pytest.param(
                [_req(), _opt()],
                ["filled", ""],
                False,
                id="optional_empty_required_filled",
            ),
            pytest.param(
                [_req(), _opt()],
                ["filled", None],
                False,
                id="optional_none_required_filled",
            ),
            pytest.param(
                [_req(), _opt()],
                ["", "something"],
                True,
                id="required_empty_optional_filled",
            ),
            pytest.param(
                [_req(), _req("other")],
                ["filled", "also filled"],
                False,
                id="all_required_filled",
            ),
            pytest.param(
                [_opt(), _opt("opt2")],
                ["", None],
                False,
                id="no_required_fields",
            ),
        ],
    )
    def test_options_unfilled(
        self,
        col_configs: list[frontend_models.DFEColumnConfig],
        outputs: list[object],
        *,
        expected: bool,
    ) -> None:
        """Test the logic for determining if required options are unfilled."""
        assert (
            add_button.AddButton._has_unfilled_required(col_configs, outputs)
            is expected
        )
