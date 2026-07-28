"""Every page in the navigation must own its URL pathname.

Application pages and docs pages share one namespace: ``DocsUI`` routes each
guide at its slug, and ``st.navigation`` refuses to start the app if two pages
claim the same pathname. Neither side can see the other — the docs registry
de-duplicates only among docs — so the overlap is checked here.
"""

import pytest

from driving_adapters.pages import constants, docs_pages


@pytest.fixture(name="docs_slugs")
def _docs_slugs() -> set[str]:
    """Return the slug every docs page is routed at."""
    registry = docs_pages.DocsRegistry(docs_pages.DOCS_DIR)
    return {page.slug for page in registry.pages}


def test_no_docs_page_shadows_an_application_page(docs_slugs: set[str]) -> None:
    # Arrange
    app_paths = {str(path) for path in constants.PagePaths}

    # Act
    collisions = app_paths & docs_slugs

    # Assert
    assert collisions == set()


def test_application_pages_do_not_share_a_url_path() -> None:
    # Arrange - a StrEnum silently aliases two members with the same value, so
    # comparing member count to value count is what catches a duplicate.
    paths = [str(path) for path in constants.PagePaths]

    # Act / Assert
    assert len(paths) == len(set(paths))
