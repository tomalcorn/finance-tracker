"""Unit tests for the docs_pages helpers module."""

import json
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from apps.pages import docs_pages, errors

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def tmp_docs_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return a temporary directory that acts as the docs root."""
    return tmp_path


@pytest.fixture
def valid_md_file(tmp_docs_dir: pathlib.Path) -> pathlib.Path:
    """Write a minimal, fully-valid markdown file and return its path."""
    content = (
        "---\n"
        "slug: getting_started\n"
        "order: 1\n"
        "icon: :book:\n"
        "---\n"
        "# Getting Started\n\n"
        "Welcome to the docs.\n"
    )
    path = tmp_docs_dir / "getting_started.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def registry(
    tmp_docs_dir: pathlib.Path,
) -> docs_pages.DocsRegistry:
    """Return a DocsRegistry pointed at a directory with one valid file."""
    content = (
        "---\n"
        "slug: getting_started\n"
        "order: 1\n"
        "icon: :material/menu_book:\n"
        "---\n"
        "# Getting Started\n\n"
        "Welcome to the docs.\n"
    )
    (tmp_docs_dir / "getting_started.md").write_text(content, encoding="utf-8")
    return docs_pages.DocsRegistry(tmp_docs_dir)


def _docs_pages_app(docs_dir: pathlib.Path, *, render_boom: bool = False) -> None:
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


# ===========================================================================
# _parse_frontmatter
# ===========================================================================


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_metadata(self):
        # Arrange
        content = "# Title\n\nBody text."

        # Act
        metadata, _ = docs_pages._parse_frontmatter(content)

        # Assert
        assert metadata == {}

    def test_no_frontmatter_returns_full_content_as_body(self):
        # Arrange
        content = "# Title\n\nBody text."

        # Act
        _, body = docs_pages._parse_frontmatter(content)

        # Assert
        assert body == content

    def test_valid_frontmatter_parses_metadata(self):
        # Arrange
        content = "---\ntitle: Hello\norder: 2\n---\nBody."

        # Act
        metadata, _ = docs_pages._parse_frontmatter(content)

        # Assert
        assert metadata == {"title": "Hello", "order": 2}

    def test_valid_frontmatter_strips_leading_whitespace_from_body(self):
        # Arrange
        content = "---\ntitle: Hello\n---\n\n\nBody starts here."

        # Act
        _, body = docs_pages._parse_frontmatter(content)

        # Assert
        assert body.startswith("Body starts here.")

    def test_empty_frontmatter_block_returns_empty_metadata(self):
        # Arrange
        content = "---\n---\nBody."

        # Act
        metadata, _ = docs_pages._parse_frontmatter(content)

        # Assert
        assert metadata == {}


# ===========================================================================
# _convert_string_to_slug
# ===========================================================================


class TestConvertStringToSlug:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Hello World", "hello_world"),
            ("already_fine", "already_fine"),
            ("kebab-case", "kebab_case"),
            ("Mixed-Case And Spaces", "mixed_case_and_spaces"),
            ("UPPER", "upper"),
        ],
    )
    def test_conversion(self, value: str, expected: str):
        # Arrange / Act
        result = docs_pages._convert_string_to_slug(value)

        # Assert
        assert result == expected


# ===========================================================================
# load_markdown_doc — happy paths
# ===========================================================================


class TestLoadMarkdownDocHappy:
    def test_returns_markdown_page_instance(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert isinstance(page, docs_pages.MarkdownPage)

    def test_slug_from_frontmatter(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert page.slug == "getting_started"

    def test_order_from_frontmatter(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert page.order == 1

    def test_icon_from_frontmatter(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert page.icon == ":book:"

    def test_title_falls_back_to_first_heading_when_no_front_matter_title(
        self,
        valid_md_file: pathlib.Path,
    ):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert page.title == "Getting Started"

    def test_front_matter_title_takes_priority_over_heading(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        content = (
            "---\n"
            "front_matter_title: Explicit Title\n"
            "slug: explicit\n"
            "order: 1\n"
            "icon: :star:\n"
            "---\n"
            "# Heading Title\n"
        )
        path = tmp_docs_dir / "explicit.md"
        path.write_text(content, encoding="utf-8")

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.title == "Explicit Title"

    def test_slug_derived_from_title_when_not_in_frontmatter(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        content = "---\norder: 1\nicon: :page_facing_up:\n---\n# My Page Title\n"
        path = tmp_docs_dir / "page.md"
        path.write_text(content, encoding="utf-8")

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        assert page.slug == "my_page_title"

    def test_order_defaults_to_9999_when_absent(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nicon: :book:\n---\n# Title\n"
        path = tmp_docs_dir / "no_order.md"
        path.write_text(content, encoding="utf-8")

        # Act
        page = docs_pages.load_markdown_doc(path)

        # Assert
        default_order = 9999
        assert page.order == default_order

    def test_content_is_body_text(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert "Welcome to the docs." in page.content


# ===========================================================================
# load_markdown_doc — error paths
# ===========================================================================


class TestLoadMarkdownDocErrors:
    def test_missing_icon_raises_missing_icon_error(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: no_icon\norder: 1\n---\n# No Icon\n"
        path = tmp_docs_dir / "no_icon.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.MissingIconError):
            docs_pages.load_markdown_doc(path)

    def test_missing_icon_error_carries_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: no_icon\norder: 1\n---\n# No Icon\n"
        path = tmp_docs_dir / "no_icon.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.MissingIconError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.path == path

    def test_non_string_icon_raises_invalid_frontmatter_error(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        content = "---\nslug: bad_icon\norder: 1\nicon: 42\n---\n# Bad Icon\n"
        path = tmp_docs_dir / "bad_icon.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.InvalidFrontmatterError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.field == "icon"

    def test_non_integer_order_raises_invalid_frontmatter_error(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        content = "---\nslug: bad_order\norder: high\nicon: :book:\n---\n# Bad Order\n"
        path = tmp_docs_dir / "bad_order.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.InvalidFrontmatterError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.field == "order"

    def test_non_integer_order_error_carries_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: bad_order\norder: high\nicon: :book:\n---\n# Bad Order\n"
        path = tmp_docs_dir / "bad_order.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.InvalidFrontmatterError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.path == path

    def test_empty_body_raises_empty_doc_body_error(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: empty\norder: 1\nicon: :book:\n---\n"
        path = tmp_docs_dir / "empty_body.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.EmptyDocBodyError):
            docs_pages.load_markdown_doc(path)

    def test_empty_body_error_carries_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: empty\norder: 1\nicon: :book:\n---\n"
        path = tmp_docs_dir / "empty_body.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.EmptyDocBodyError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.path == path

    def test_invalid_slug_raises_invalid_frontmatter_error(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        # A slug with characters that survive _convert_string_to_slug but fail the
        # regex (e.g. leading/trailing underscores after conversion).
        content = "---\nslug: '!!!'\norder: 1\nicon: :book:\n---\n# Bad Slug\n"
        path = tmp_docs_dir / "bad_slug.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.InvalidFrontmatterError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert exc_info.value.field == "slug"

    def test_invalid_frontmatter_error_is_subclass_of_docs_error(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        content = "---\nslug: no_icon\norder: 1\n---\n# No Icon\n"
        path = tmp_docs_dir / "no_icon2.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.DocsError):
            docs_pages.load_markdown_doc(path)


# ===========================================================================
# DocsRegistry.__init__
# ===========================================================================


class TestDocsRegistryInit:
    def test_raises_docs_directory_error_for_missing_dir(self, tmp_path: pathlib.Path):
        # Arrange
        non_existent = tmp_path / "does_not_exist"

        # Act / Assert
        with pytest.raises(errors.DocsDirectoryError):
            docs_pages.DocsRegistry(non_existent)

    def test_docs_directory_error_carries_path(self, tmp_path: pathlib.Path):
        # Arrange
        non_existent = tmp_path / "does_not_exist"

        # Act / Assert
        with pytest.raises(errors.DocsDirectoryError) as exc_info:
            docs_pages.DocsRegistry(non_existent)

        assert exc_info.value.docs_dir == non_existent

    def test_succeeds_for_existing_directory(self, tmp_docs_dir: pathlib.Path):
        # Arrange / Act
        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Assert
        assert reg._docs_dir == tmp_docs_dir


# ===========================================================================
# DocsRegistry.pages
# ===========================================================================


class TestDocsRegistryPages:
    def test_returns_list_of_markdown_pages(self, registry: docs_pages.DocsRegistry):
        # Arrange / Act
        pages = registry.pages

        # Assert
        assert all(isinstance(p, docs_pages.MarkdownPage) for p in pages)

    def test_pages_are_sorted_by_order(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        for i, (slug, order) in enumerate(
            [("alpha", 3), ("beta", 1), ("gamma", 2)],
        ):
            content = (
                f"---\nslug: {slug}\norder: {order}\nicon: "
                f":book:\n---\n# {slug.title()}\n"
            )
            (tmp_docs_dir / f"doc_{i}.md").write_text(content, encoding="utf-8")

        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act
        pages = reg.pages

        # Assert
        assert [p.slug for p in pages] == ["beta", "gamma", "alpha"]

    def test_raises_empty_docs_directory_error_when_no_md_files(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.EmptyDocsDirectoryError):
            _ = reg.pages

    def test_empty_docs_directory_error_carries_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.EmptyDocsDirectoryError) as exc_info:
            _ = reg.pages

        assert exc_info.value.docs_dir == tmp_docs_dir

    def test_raises_duplicate_slug_error(self, tmp_docs_dir: pathlib.Path):
        # Arrange — two different files that resolve to the same slug
        for filename, title in [("doc_a.md", "My Topic"), ("doc_b.md", "My Topic")]:
            content = f"---\norder: 1\nicon: :book:\n---\n# {title}\n"
            (tmp_docs_dir / filename).write_text(content, encoding="utf-8")

        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.DuplicateSlugError):
            _ = reg.pages

    def test_duplicate_slug_error_carries_slug(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        for filename, title in [("doc_a.md", "My Topic"), ("doc_b.md", "My Topic")]:
            content = f"---\norder: 1\nicon: :book:\n---\n# {title}\n"
            (tmp_docs_dir / filename).write_text(content, encoding="utf-8")

        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.DuplicateSlugError) as exc_info:
            _ = reg.pages

        assert exc_info.value.slug == "my_topic"

    def test_pages_result_is_cached(self, registry: docs_pages.DocsRegistry):
        # Arrange / Act
        first = registry.pages
        second = registry.pages

        # Assert
        assert first is second


class TestDocsUIBuildPages:
    def test_build_pages_emits_expected_page_manifest(
        self,
        registry: docs_pages.DocsRegistry,
    ):
        # Arrange
        at = AppTest.from_function(
            _docs_pages_app,
            kwargs={"docs_dir": registry._docs_dir},
        )

        # Act
        at.run()
        manifest = json.loads(at.json[0].value)

        # Assert
        assert manifest == [
            {
                "title": "Getting Started",
                "icon": ":material/menu_book:",
                "url_path": "getting_started",
            },
        ]
        assert any("Welcome to the docs." in item.value for item in at.markdown)

    def test_render_exception_is_wrapped_as_page_render_error(
        self,
        registry: docs_pages.DocsRegistry,
    ):
        # Arrange
        at = AppTest.from_function(
            _docs_pages_app,
            kwargs={"docs_dir": registry._docs_dir, "render_boom": True},
        )

        # Act
        at.run()

        # Assert
        assert len(at.exception) == 1
        assert (
            "Failed to render page 'getting_started': render boom"
            in at.exception[0].message
        )
