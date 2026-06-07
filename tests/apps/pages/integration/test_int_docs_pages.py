"""Integration tests for the docs_pages module.

These tests exercise the full stack — file I/O → frontmatter parsing →
domain model → registry → Streamlit adapter — against real files on disk,
without mocking internal collaborators.  They are slower and more coupled
than the unit tests, but catch wiring issues that mocks cannot.
"""

import json
import pathlib
from collections.abc import Callable

import pytest
from streamlit.testing import v1 as st_test

from apps.pages import docs_pages, errors

# ===========================================================================
# Helpers
# ===========================================================================


def _write_doc(  # noqa: PLR0913 - needed for test
    directory: pathlib.Path,
    filename: str,
    *,
    slug: str | None = None,
    order: int | str = 1,
    icon: str = ":material/menu_book:",
    title: str = "Test Page",
    body: str = "Some content.",
    front_matter_title: str | None = None,
) -> pathlib.Path:
    """Write a markdown file with the given frontmatter and return the path."""
    fm_lines = []
    if slug is not None:
        fm_lines.append(f"slug: {slug}")
    if isinstance(order, int):
        fm_lines.append(f"order: {order}")
    else:
        fm_lines.append(f"order: {order}")  # intentionally bad for error tests
    fm_lines.append(f"icon: {icon}")
    if front_matter_title:
        fm_lines.append(f"front_matter_title: {front_matter_title}")

    frontmatter = "---\n" + "\n".join(fm_lines) + "\n---\n"
    content = frontmatter + f"# {title}\n\n{body}\n"
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def docs_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return a temporary docs directory."""
    return tmp_path


@pytest.fixture
def populated_docs_dir(docs_dir: pathlib.Path) -> pathlib.Path:
    """Return docs directory with three valid, ordered pages."""
    _write_doc(docs_dir, "intro.md", slug="intro", order=1, title="Introduction")
    _write_doc(docs_dir, "guide.md", slug="guide", order=2, title="Guide")
    _write_doc(docs_dir, "reference.md", slug="reference", order=3, title="Reference")
    return docs_dir


# ===========================================================================
# Full pipeline: file → MarkdownPage
# ===========================================================================


class TestFullPipelineFileToPage:
    def test_page_loaded_from_real_file_has_correct_slug(self, docs_dir: pathlib.Path):
        # Arrange
        _write_doc(docs_dir, "my_doc.md", slug="my_doc", order=1, title="My Doc")
        path = docs_dir / "my_doc.md"

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.slug == "my_doc"

    def test_page_loaded_from_real_file_has_correct_title(self, docs_dir: pathlib.Path):
        # Arrange
        _write_doc(docs_dir, "titled.md", slug="titled", order=1, title="Full Title")
        path = docs_dir / "titled.md"

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.title == "Full Title"

    def test_page_content_survives_round_trip(self, docs_dir: pathlib.Path):
        # Arrange
        _write_doc(
            docs_dir,
            "content.md",
            slug="content_page",
            order=1,
            title="Content Page",
            body="Here is my **body** text.",
        )
        path = docs_dir / "content.md"

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert "Here is my **body** text." in page.content

    def test_front_matter_title_overrides_heading(self, docs_dir: pathlib.Path):
        # Arrange
        _write_doc(
            docs_dir,
            "override.md",
            slug="override",
            order=1,
            title="Heading Title",
            front_matter_title="FM Title",
        )
        path = docs_dir / "override.md"

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.title == "FM Title"

    def test_slug_derived_from_heading_when_not_in_frontmatter(
        self,
        docs_dir: pathlib.Path,
    ):
        # Arrange — no slug in frontmatter; title becomes the slug source
        content = "---\norder: 1\nicon: :book:\n---\n# Derived From Heading\n"
        path = docs_dir / "derived.md"
        path.write_text(content, encoding="utf-8")

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.slug == "derived_from_heading"

    @pytest.mark.parametrize(
        ("raw_order", "expected"),
        [
            (1, 1),
            (99, 99),
            (9999, 9999),
        ],
    )
    def test_order_is_loaded_correctly(
        self,
        docs_dir: pathlib.Path,
        raw_order: int,
        expected: int,
    ):
        # Arrange
        _write_doc(
            docs_dir,
            f"order_{raw_order}.md",
            slug=f"o{raw_order}",
            order=raw_order,
        )

        # Act
        page = docs_pages.load_markdown_doc(docs_dir / f"order_{raw_order}.md")

        # Assert
        assert page.order == expected


# ===========================================================================
# Full pipeline: DocsRegistry
# ===========================================================================


class TestDocsRegistryIntegration:
    def test_registry_loads_all_files_in_directory_and_orders_them(
        self,
        populated_docs_dir: pathlib.Path,
    ):
        # Arrange
        reg = docs_pages.DocsRegistry(populated_docs_dir)

        # Act
        pages = reg.pages

        # Assert
        expected_pages_len = 3
        assert all(
            k[
                len(pages) == expected_pages_len,
                [p.slug for p in pages] == ["intro", "guide", "reference"],
            ],
        )

    def test_registry_ignores_non_md_files(self, docs_dir: pathlib.Path):
        # Arrange
        _write_doc(docs_dir, "valid.md", slug="valid", order=1)
        (docs_dir / "readme.txt").write_text("not a doc", encoding="utf-8")
        reg = docs_pages.DocsRegistry(docs_dir)

        # Act
        pages = reg.pages

        # Assert
        assert len(pages) == 1

    def test_registry_raises_on_missing_directory(self, tmp_path: pathlib.Path):
        # Arrange
        missing = tmp_path / "ghost"

        # Act / Assert
        with pytest.raises(errors.DocsDirectoryError):
            docs_pages.DocsRegistry(missing)

    def test_registry_raises_on_empty_directory(self, docs_dir: pathlib.Path):
        # Arrange
        reg = docs_pages.DocsRegistry(docs_dir)

        # Act / Assert
        with pytest.raises(errors.EmptyDocsDirectoryError):
            _ = reg.pages

    def test_registry_raises_on_duplicate_slugs(self, docs_dir: pathlib.Path):
        # Arrange — two files whose headings produce the same slug
        _write_doc(docs_dir, "a.md", order=1, title="Same Title")
        _write_doc(docs_dir, "b.md", order=2, title="Same Title")
        reg = docs_pages.DocsRegistry(docs_dir)

        # Act / Assert
        with pytest.raises(errors.DuplicateSlugError):
            _ = reg.pages

    def test_registry_propagates_invalid_frontmatter_error(
        self,
        docs_dir: pathlib.Path,
    ):
        # Arrange — one good file, one bad (missing icon)
        _write_doc(docs_dir, "good.md", slug="good", order=1)
        bad_content = "---\nslug: bad\norder: 1\n---\n# Bad\n"
        (docs_dir / "bad.md").write_text(bad_content, encoding="utf-8")
        reg = docs_pages.DocsRegistry(docs_dir)

        # Act / Assert
        with pytest.raises(errors.InvalidFrontmatterError):
            _ = reg.pages

    def test_pages_property_is_cached_across_calls(
        self,
        populated_docs_dir: pathlib.Path,
    ):
        # Arrange
        reg = docs_pages.DocsRegistry(populated_docs_dir)
        first = reg.pages

        # Act
        second = reg.pages

        # Assert
        assert first is second


# ===========================================================================
# Full pipeline: DocsUI adapter
# ===========================================================================


class TestDocsUIIntegration:
    def test_build_pages_emits_expected_manifest(
        self,
        populated_docs_dir: pathlib.Path,
        app_tester_getter: Callable[..., st_test.AppTest],
    ):
        # Arrange
        reg = docs_pages.DocsRegistry(populated_docs_dir)
        at = app_tester_getter(
            docs_dir=populated_docs_dir,
        )

        # Act
        at.run()
        manifest = json.loads(at.json[0].value)

        # Assert
        assert all(
            [
                len(manifest) == len(reg.pages),
                manifest
                == [
                    {
                        "title": "Introduction",
                        "icon": ":material/menu_book:",
                        "url_path": "intro",
                    },
                    {
                        "title": "Guide",
                        "icon": ":material/menu_book:",
                        "url_path": "guide",
                    },
                    {
                        "title": "Reference",
                        "icon": ":material/menu_book:",
                        "url_path": "reference",
                    },
                ],
                [item["url_path"] for item in manifest] == [p.slug for p in reg.pages],
                [item["title"] for item in manifest] == [p.title for p in reg.pages],
            ],
        )

    def test_docs_ui_build_pages_propagates_registry_errors(
        self,
        docs_dir: pathlib.Path,
    ):
        # Arrange — empty directory means .pages will raise
        reg = docs_pages.DocsRegistry(docs_dir)

        # Act / Assert
        with pytest.raises(errors.EmptyDocsDirectoryError):
            docs_pages.DocsUI(reg).build_pages()
