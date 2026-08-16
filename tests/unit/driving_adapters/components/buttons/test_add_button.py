"""Unit tests for the add button free functions."""

from typing import TYPE_CHECKING

import pandas as pd
import pydantic
import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from tests import conftest

from domain import entities
from driving_adapters.components.buttons import add_button
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from driving_adapters.components.dfes import data_source as data_source_mod

USER_ID = "auth0|test-user-1"


class _RowModel(pydantic.BaseModel):
    name: str
    user_id: str


def _config(
    *,
    data_source: "data_source_mod.GridDataSource",
) -> frontend_models.DFEConfig:
    """Build a minimal grid config for the add-button tests."""
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id="test_table",
            data_source=data_source,
        ),
        display=frontend_models.GridDisplay(columns=[], sample_data=pd.DataFrame()),
    )


def test_submit_new_row_saves_the_entity_built_by_the_port(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange
    data_source = build_stub_data_source(
        context={"user_id": USER_ID},
        model=_RowModel,
    )
    config = _config(data_source=data_source)

    # Act
    add_button._submit_new_row(config.source, {"name": "Savings"})

    # Assert - the row went through the gate and the resulting entity was saved
    assert data_source.saved == [_RowModel(name="Savings", user_id=USER_ID)]


class _LinkedRowModel(pydantic.BaseModel):
    name: str
    user_id: str
    parent_id: str | None = None


def test_submit_new_row_merges_extra_row_values(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> None:
    # Arrange - the expense categories grid parents new rows to its budget
    # tracker via extra_row_values, so they survive the tab's own row predicate.
    data_source = build_stub_data_source(
        context={"user_id": USER_ID},
        model=_LinkedRowModel,
    )
    config = frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            grid_id="expense_categories",
            data_source=data_source,
            extra_row_values={"parent_id": "bt-expenses"},
        ),
        display=frontend_models.GridDisplay(columns=[], sample_data=pd.DataFrame()),
    )

    # Act
    add_button._submit_new_row(config.source, {"name": "Rent"})

    # Assert
    assert data_source.saved == [
        _LinkedRowModel(
            name="Rent",
            user_id=USER_ID,
            parent_id="bt-expenses",
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
def _app_tester(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
) -> st_test.AppTest:
    source = build_stub_data_source(
        context={"user_id": USER_ID},
        model=entities.ExpensePaymentModel,
    )
    return st_test.AppTest.from_function(
        _dialog_wrapper,
        default_timeout=120,
        kwargs={"config": _config(data_source=source)},
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
