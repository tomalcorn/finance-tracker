"""Shared fixtures for the pages."""

from collections.abc import Callable
from typing import Any

import pytest
import streamlit.testing.v1 as st_test


# Can't type docs_dir, doesn't work with AppTest
def _docs_pages_app(docs_dir, *, render_boom: bool = False) -> None:  # noqa: ANN001
    from unittest import mock

    import streamlit as st

    from apps.pages import docs_pages

    registry = docs_pages.DocsRegistry(docs_dir)
    pages = docs_pages.DocsUI(registry).build_pages()
    st.json(
        [
            {
                "title": page.title,
                "icon": page.icon,
                "url_path": page.url_path,
            }
            for page in pages
        ],
    )

    if render_boom:
        with mock.patch("streamlit.markdown", side_effect=RuntimeError("render boom")):
            st.navigation(pages).run()
        return

    st.navigation(pages).run()


@pytest.fixture(name="app_tester_getter")
def _app_tester_getter() -> Callable[..., st_test.AppTest]:

    def _app_tester(**kwargs: dict[str, Any]) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _docs_pages_app,
            default_timeout=120,
            kwargs=kwargs,
        )

    return _app_tester
