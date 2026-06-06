"""Helpers for building Streamlit docs pages from markdown files."""

import collections
import functools
import pathlib
from typing import Annotated

import pydantic
import streamlit as st
import yaml
from streamlit.navigation import page as st_page

from apps.pages import errors

DOCS_DIR = pathlib.Path(__file__).resolve().parents[2] / "docs"


# == Domain ==


def _convert_string_to_slug(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


SLUG = Annotated[
    str,
    pydantic.StringConstraints(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$"),
    pydantic.BeforeValidator(_convert_string_to_slug),
]
SLUG_ADAPTER = pydantic.TypeAdapter(SLUG)


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Return (metadata, body)."""
    if not content.startswith("---"):
        return {}, content

    _, raw, body = content.split("---", 2)
    metadata = yaml.safe_load(raw) or {}

    return metadata, body.lstrip()


class MarkdownPage(pydantic.BaseModel):
    """A page pulled from a markdown file."""

    title: Annotated[str, pydantic.Field(description="Title of the doc")]
    slug: SLUG
    order: Annotated[
        pydantic.PositiveInt,
        pydantic.Field(description="Order for rendering in UI"),
    ]
    icon: Annotated[str, pydantic.Field(description="Streamlit icon for the page")]
    content: Annotated[str, pydantic.Field(description="Body content", min_length=0)]


# == Use Case ==


def load_markdown_doc(path: pathlib.Path) -> MarkdownPage:
    """Load a MarkdownPage from a markdown file.

    Raises:
        errors.EmptyDocBodyError: file has frontmatter but no body.
        errors.InvalidFrontmatterError: a frontmatter field has an unusable value.
        errors.MissingIconError: icon field is absent or not a string.

    """
    raw = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(raw)

    # Title: prefer explicit frontmatter, else first heading from body.
    if metadata.get("front_matter_title"):
        title = metadata["front_matter_title"]
    else:
        lines = body.splitlines()
        if not lines:
            raise errors.EmptyDocBodyError(path)
        title = lines[0].lstrip("# ").strip()

    # Slug
    try:
        slug = SLUG_ADAPTER.validate_python(metadata.get("slug") or title)
    except pydantic.ValidationError as exc:
        raise errors.InvalidFrontmatterError(
            path,
            field="slug",
            reason=str(exc),
        ) from exc

    # Order
    raw_order = metadata.get("order", 9999)
    try:
        order = int(raw_order)
    except (TypeError, ValueError) as exc:
        raise errors.InvalidFrontmatterError(
            path,
            field="order",
            reason=f"expected an integer, got {raw_order!r}",
        ) from exc

    # Icon — must be a non-empty string
    icon = metadata.get("icon")
    if not isinstance(icon, str) or not icon:
        if icon is None:
            raise errors.MissingIconError(path)
        raise errors.InvalidFrontmatterError(
            path,
            field="icon",
            reason=f"expected a non-empty string, got {icon!r}",
        )

    try:
        return MarkdownPage(
            title=title,
            slug=slug,
            order=order,
            icon=icon,
            content=body,
        )
    except pydantic.ValidationError as exc:
        # Translate pydantic errors for any remaining field constraints.
        raise errors.InvalidFrontmatterError(
            path,
            field="(model)",
            reason=str(exc),
        ) from exc


class DocsRegistry:
    """Registry for docs pages loaded from a directory."""

    def __init__(self, docs_dir: pathlib.Path) -> None:
        """Construct the DocsRegistry.

        Raises:
            errors.DocsDirectoryError: docs_dir does not exist.

        """
        if not docs_dir.is_dir():
            raise errors.DocsDirectoryError(docs_dir)
        self._docs_dir = docs_dir

    @functools.cached_property
    def pages(self) -> list[MarkdownPage]:
        """Sorted list of pages.

        Raises:
            errors.EmptyDocsDirectoryError: no markdown files found.
            errors.DuplicateSlugError: two files resolved to the same slug.

        """
        loaded = [load_markdown_doc(p) for p in self._docs_dir.glob("*.md")]

        if not loaded:
            raise errors.EmptyDocsDirectoryError(self._docs_dir)

        # Detect duplicate slugs before handing pages to the router.
        slug_index: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
        for page in loaded:
            slug_index[page.slug].append(self._docs_dir / f"{page.slug}.md")

        dupes = {slug: paths for slug, paths in slug_index.items() if len(paths) > 1}
        if dupes:
            slug, paths = next(iter(dupes.items()))
            raise errors.DuplicateSlugError(slug, paths)

        return sorted(loaded, key=lambda p: p.order)


# == Streamlit adapter layer ==


class DocsUI:
    """Streamlit adapter to render the DocsRegistry."""

    def __init__(self, registry: DocsRegistry) -> None:
        """Construct the DocsUI."""
        self.registry = registry

    def _to_streamlit_page(self, doc: MarkdownPage) -> st_page.StreamlitPage:
        def _render() -> None:
            # Translate unexpected render-time exceptions into adapter errors.
            try:
                st.markdown(doc.content)
            except Exception as exc:
                raise errors.PageRenderError(doc.slug, exc) from exc

        return st.Page(
            _render,
            title=doc.title,
            icon=doc.icon,
            url_path=doc.slug,
        )

    def build_pages(self) -> list[st_page.StreamlitPage]:
        """Build the StreamlitPage items for all registered docs."""
        return [self._to_streamlit_page(page) for page in self.registry.pages]
