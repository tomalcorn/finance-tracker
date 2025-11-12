"""Unit tests for the sort button module."""

import pytest
import streamlit as st
import streamlit.testing.v1 as st_test
from src.libs import config, models
from src.libs.buttons import sort
from tests import conftest


def _sort_button_dialog_wrapper() -> None:
    """Call the _sorting_button_dialog method."""
    import streamlit as st
    from src.libs import config
    from src.libs.buttons import sort

    dfe_configs = [
        config.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting="asc",
        ),
        config.DFEColumnConfig(
            column_name="col2",
            column_config={},
            input_widget=st.number_input,
            sorting="desc",
        ),
    ]

    sort_button = sort.SortButton("test_table", dfe_configs)

    return sort_button._sorting_button_dialog()


@pytest.fixture(name="app_tester")
def _app_tester() -> st_test.AppTest:
    return st_test.AppTest.from_function(
        _sort_button_dialog_wrapper,
        default_timeout=120,
    )


def test_override_configs_from_session_state_returns_none() -> None:
    """Test _override_configs_from_session_state returns None when no session state."""
    # Arrange
    dfe_configs = [
        config.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting="asc",
        ),
    ]
    sort_button = sort.SortButton("test_table", dfe_configs)

    # Act
    result = sort_button._override_configs_from_session_state()

    # Assert
    assert result is None


def test_override_configs_from_session_state_returns_configs() -> None:
    """Test _override_configs_from_session_state returns configs from session state."""
    # Arrange
    dfe_configs = [
        config.DFEColumnConfig(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting="asc",
        ),
    ]
    sort_button = sort.SortButton("test_table", [])

    # Set session state
    session_key = f"test_table_{models.SSKeys.COL_CONFIGS}"
    st.session_state[session_key] = dfe_configs

    # Act
    result = sort_button._override_configs_from_session_state()

    # Assert
    assert result == dfe_configs


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
        expected_sorting: str | None,
    ) -> None:
        """Test _sorting_button_dialog updates sorting based on user input."""
        # Act - render button and make selections
        app_tester.run()
        for i in range(len(app_tester.selectbox)):
            app_tester.selectbox[i].select(new_selection)
        app_tester.button("test_table_apply_sorting_button").click()
        app_tester.run()

        # Assert - sorting updated correctly
        updated_col_configs: list[config.DFEColumnConfig] = app_tester.session_state[
            f"test_table_{models.SSKeys.COL_CONFIGS}"
        ]
        actual_sorting = [col_config.sorting for col_config in updated_col_configs]
        assert actual_sorting == expected_sorting

    def dummy_test(self) -> None:
        """Dummy test to ensure at least one test is present."""
        assert 1 == 2
