"""Unit tests for the docs_pages helpers module."""

import json
import pathlib
from collections.abc import Callable

import pytest
from streamlit.testing import v1 as st_test

from driving_adapters.pages import docs_pages, errors

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


# ===========================================================================
# _parse_frontmatter
# ===========================================================================


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_metadata_and_full_content_as_body(self):
        # Arrange
        content = "# Title\n\nBody text."

        # Act
        metadata, body = docs_pages._parse_frontmatter(content)

        # Assert
        assert all([metadata == {}, body == content])

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
    def test_valid_doc_populates_core_fields(self, valid_md_file: pathlib.Path):
        # Arrange / Act
        page = docs_pages.load_markdown_doc(valid_md_file)

        # Assert
        assert all(
            [
                isinstance(page, docs_pages.MarkdownPage),
                page.slug == "getting_started",
                page.order == 1,
                page.icon == ":book:",
                page.title == "Getting Started",
                "Welcome to the docs." in page.content,
            ],
        )

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


# ===========================================================================
# load_markdown_doc — error paths
# ===========================================================================


class TestLoadMarkdownDocErrors:
    def test_missing_icon_error_type_and_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: no_icon\norder: 1\n---\n# No Icon\n"
        path = tmp_docs_dir / "no_icon.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.MissingIconError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert all([exc_info.value.path == path])

    def test_non_string_icon_error_type_and_field(
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

        assert all([exc_info.value.field == "icon"])

    def test_non_integer_order_error_type_and_field(
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

        assert all([exc_info.value.field == "order", exc_info.value.path == path])

    def test_empty_body_error_type_and_path(self, tmp_docs_dir: pathlib.Path):
        # Arrange
        content = "---\nslug: empty\norder: 1\nicon: :book:\n---\n"
        path = tmp_docs_dir / "empty_body.md"
        path.write_text(content, encoding="utf-8")

        # Act / Assert
        with pytest.raises(errors.EmptyDocBodyError) as exc_info:
            docs_pages.load_markdown_doc(path)

        assert all([exc_info.value.path == path])

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
    def test_missing_dir_error_type_and_path(self, tmp_path: pathlib.Path):
        # Arrange
        non_existent = tmp_path / "does_not_exist"

        # Act / Assert
        with pytest.raises(errors.DocsDirectoryError) as exc_info:
            docs_pages.DocsRegistry(non_existent)

        assert all([exc_info.value.docs_dir == non_existent])

    def test_succeeds_for_existing_directory(self, tmp_docs_dir: pathlib.Path):
        # Arrange / Act
        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Assert
        assert reg._docs_dir == tmp_docs_dir


# ===========================================================================
# DocsRegistry.pages
# ===========================================================================


class TestDocsRegistryPages:
    def test_pages_are_markdown_pages_and_sorted_by_order(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
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
        assert all(
            [
                all(isinstance(p, docs_pages.MarkdownPage) for p in pages),
                [p.slug for p in pages] == ["beta", "gamma", "alpha"],
            ],
        )

    def test_empty_directory_error_type_and_path(
        self,
        tmp_docs_dir: pathlib.Path,
    ):
        # Arrange
        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.EmptyDocsDirectoryError) as exc_info:
            _ = reg.pages
        assert all([exc_info.value.docs_dir == tmp_docs_dir])

    def test_duplicate_slug_error_type_and_slug(self, tmp_docs_dir: pathlib.Path):
        # Arrange — two different files that resolve to the same slug
        for filename, title in [("doc_a.md", "My Topic"), ("doc_b.md", "My Topic")]:
            content = f"---\norder: 1\nicon: :book:\n---\n# {title}\n"
            (tmp_docs_dir / filename).write_text(content, encoding="utf-8")

        reg = docs_pages.DocsRegistry(tmp_docs_dir)

        # Act / Assert
        with pytest.raises(errors.DuplicateSlugError) as exc_info:
            _ = reg.pages
        assert all([exc_info.value.slug == "my_topic"])

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
        app_tester_getter: Callable[..., st_test.AppTest],
    ):
        # Arrange
        at = app_tester_getter(docs_dir=registry._docs_dir)

        # Act
        at.run()
        manifest = json.loads(at.json[0].value)

        # Assert
        assert all(
            [
                manifest
                == [
                    {
                        "title": "Getting Started",
                        "icon": ":material/menu_book:",
                        "url_path": "getting_started",
                    },
                ],
                any("Welcome to the docs." in item.value for item in at.markdown),
            ],
        )

    def test_render_exception_is_wrapped_as_page_render_error(
        self,
        registry: docs_pages.DocsRegistry,
        app_tester_getter: Callable[..., st_test.AppTest],
    ):
        # Arrange
        at = app_tester_getter(docs_dir=registry._docs_dir, render_boom=True)

        # Act
        at.run()

        # Assert
        assert all(
            [
                len(at.exception) == 1,
                (
                    "Failed to render page 'getting_started': render boom"
                    in at.exception[0].message
                ),
            ],
        )
