"""Unit tests for the sort button module."""

import pytest
import streamlit.testing.v1 as st_test
from tests import conftest

from apps.buttons import sort
from libs import constants, frontend_models


def _sort_button_dialog_wrapper() -> None:
    """Call the _sorting_button_dialog method."""
    import streamlit as st

    from apps.buttons import sort
    from libs import constants, frontend_models

    dfe_configs = [
        frontend_models.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting=constants.SortingValues.ASC,
        ),
        frontend_models.DFEColumnConfig(
            column_name="col2",
            column_config={},
            input_widget=st.number_input,
            sorting=constants.SortingValues.DESC,
        ),
    ]

    sort_button = sort.SortButton("test_table")

    return sort_button._sorting_button_dialog(dfe_configs)


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _sort_button_dialog_wrapper,
        default_timeout=120,
    )


def test_current_css_style_no_sorting(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test _current_css_style returns normal style when no sorting applied."""
    # Arrange
    col_configs_no_sorting = [
        col_configs[i].model_copy(update={"sorting": None})
        for i in range(len(col_configs))
    ]
    sort_button = sort.SortButton("test_table_1")

    # Act
    result = sort_button._current_css_style(col_configs_no_sorting)

    # Assert
    assert result == sort_button.css_style_normal


def test_current_css_style_with_sorting(
    col_configs: list[frontend_models.DFEColumnConfig],
) -> None:
    """Test _current_css_style returns active style when sorting is applied."""
    # Arrange
    col_configs_w_sorting = [col_configs[0].model_copy(update={"sorting": "asc"})]
    sort_button = sort.SortButton("test_table_2")

    # Act
    result = sort_button._current_css_style(col_configs_w_sorting)

    # Assert
    assert result == sort_button.css_style_active


class TestSortButtonDialog:
    """Tests for the SortButton dialog method."""

    def test_sort_button_dialog_text_renders(self, app_tester: st_test.AppTest) -> None:
        """Test _sorting_button_dialog renders text successfully."""
        # Arrange
        expected_dialog_text = "Sort **test_table** by:"
        expected_selectbox_labels = ["col1", "col2"]

        # Act - render button
        app_tester.run()

        # Assert - dialog text present
        actual_selectbox_labels = [
            selectbox.label for selectbox in app_tester.selectbox
        ]
        assert all(
            [
                expected_dialog_text in conftest.get_rendered_texts(app_tester),
                all(
                    label in actual_selectbox_labels
                    for label in expected_selectbox_labels
                ),
            ],
        )

    def test_sort_button_dialog_sorting_options(
        self,
        app_tester: st_test.AppTest,
    ) -> None:
        """Test _sorting_button_dialog presents sorting options correctly."""
        # Arrange
        expected_options = ["Ascending", "Descending", "None"]
        expected_default_indices = [0, 1]  # asc for col1, desc for col2

        # Act - render button
        app_tester.run()

        # Assert - sorting options and defaults correct
        assert all(
            selectbox.options == expected_options
            and selectbox.index == expected_default_indices[i]
            for i, selectbox in enumerate(app_tester.selectbox)
        )

    @pytest.mark.parametrize(
        ("new_selection", "expected_sorting"),
        [
            ("asc", ["asc", "asc"]),
            ("desc", ["desc", "desc"]),
        ],
    )
    def test_sort_button_dialog_updates_sorting(
        self,
        app_tester: st_test.AppTest,
        new_selection: str,
        expected_sorting: list[str | None],
    ) -> None:
        """Test _sorting_button_dialog updates sorting based on user input."""
        # Act - render button and make selections
        app_tester.run()
        for i in range(len(app_tester.selectbox)):
            app_tester.selectbox[i].select(new_selection)
        app_tester.button("test_table_apply_sorting_button").click()
        app_tester.run()

        # Assert - sorting updated correctly
        updated_col_configs: list[frontend_models.DFEColumnConfig] = (
            app_tester.session_state[f"test_table_{constants.SSKeys.COL_CONFIGS}"]
        )
        actual_sorting = [col_config.sorting for col_config in updated_col_configs]
        assert actual_sorting == expected_sorting
