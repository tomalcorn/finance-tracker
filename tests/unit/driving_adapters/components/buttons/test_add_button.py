"""Unit tests for the add button free functions."""

import typing
from unittest import mock

import pandas as pd
import pydantic
import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from tests import conftest

from domain import entities
from driving_adapters.components.buttons import add_button
from driving_adapters.models import frontend_models


@pytest.fixture(autouse=True)
def _mock_current_user() -> typing.Generator[None, None, None]:
    """Patch the current user lookup so add button tests avoid Streamlit auth."""
    with mock.patch.object(
        add_button.auth,
        "get_current_user",
        return_value="auth0|test-user-1",
    ):
        yield


class _RowModel(pydantic.BaseModel):
    name: str
    user_id: str


class _StubDataSource:
    """GridDataSource stub recording the batches applied through the port."""

    def __init__(self) -> None:
        self.applied: list[entities.BackendUpdates] = []

    def rows(self) -> list[pydantic.BaseModel]:
        return []

    # column_name is unused: the stub only satisfies the GridDataSource protocol.
    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return set()

    def apply(self, updates: entities.BackendUpdates) -> None:
        self.applied.append(updates)


def _config(
    *,
    backend_model: type[pydantic.BaseModel],
    data_source: _StubDataSource,
) -> frontend_models.DFEConfig:
    """Build a minimal grid config for the add-button tests."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table="test_table",
            backend_model=backend_model,
            data_source=data_source,
        ),
        display=frontend_models.GridDisplay(columns=[], sample_data=pd.DataFrame()),
    )


def test_submit_new_row_applies_through_data_source() -> None:
    # Arrange
    data_source = _StubDataSource()
    config = _config(backend_model=_RowModel, data_source=data_source)

    # Act
    add_button._submit_new_row(config.source, {"name": "Savings"})

    # Assert
    assert data_source.applied == [
        entities.BackendUpdates(
            added_rows=[{"name": "Savings", "user_id": "auth0|test-user-1"}],
        ),
    ]


def _dialog_wrapper(config: "frontend_models.DFEConfig") -> None:
    """Render the add-row dialog for AppTest.

    ``config`` is injected via AppTest ``kwargs`` because from_function re-runs
    this body in a fresh namespace where module-level names aren't visible.
    """
    import streamlit as st  # noqa: F401 - needed for app_test from_function

    from driving_adapters.components.buttons import add_button

    add_button._add_row_dialog(config.source, config.display)


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _dialog_wrapper,
        default_timeout=120,
        kwargs={
            "config": _config(
                backend_model=entities.ExpensePaymentModel,
                data_source=_StubDataSource(),
            ),
        },
    )


def test_add_row_dialog_renders(app_tester: st_test.AppTest) -> None:
    # Act
    app_tester.run()

    # Assert
    submit_button_key_rendered = any(
        btn.key == "test_table_submit_new_row_button" for btn in app_tester.button
    )
    dialog_text_rendered = "Add a new row to Test Table" in conftest.get_rendered_texts(
        app_tester,
    )
    assert all([submit_button_key_rendered, dialog_text_rendered])


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
        assert add_button._has_unfilled_required(col_configs, outputs) is expected
