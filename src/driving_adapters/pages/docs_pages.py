"""Helpers for building Streamlit docs pages from markdown files."""

import collections
import functools
import pathlib
import re
from typing import TYPE_CHECKING, Annotated, cast

import pydantic
import streamlit as st
import yaml

from driving_adapters.pages import errors

if TYPE_CHECKING:
    from streamlit.navigation import page as st_page

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


def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """Return (metadata, body)."""
    if not content.startswith("---\n"):
        return {}, content

    try:
        _, raw, body = content.split("---\n", 2)
    except ValueError:
        return {}, content

    raw_lines = raw.splitlines()
    metadata: dict[str, object] = {}
    for line in raw_lines:
        if not line.strip():
            continue

        if ":" not in line:
            msg = f"invalid frontmatter line: {line!r}"
            raise yaml.YAMLError(msg)

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Treat icon-style values like :book: and :material/menu_book: as literal
        # strings instead of YAML tags.
        if re.fullmatch(r":[^:]+:", value):
            parsed_value: str | int = value
        else:
            parsed_value = yaml.safe_load(value)

        metadata[key] = parsed_value

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
    if (front_matter_title := metadata.get("front_matter_title")) and isinstance(
        front_matter_title,
        str,
    ):
        title = front_matter_title
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
    raw_order = cast("int | str", metadata.get("order", 9999))
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
        loaded = [(p, load_markdown_doc(p)) for p in self._docs_dir.glob("*.md")]

        if not loaded:
            raise errors.EmptyDocsDirectoryError(self._docs_dir)

        # Detect duplicate slugs before handing pages to the router; report the
        # real source files that collided, not the slug they resolved to.
        slug_index: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
        for path, page in loaded:
            slug_index[page.slug].append(path)

        dupes = {slug: paths for slug, paths in slug_index.items() if len(paths) > 1}
        if dupes:
            slug, paths = next(iter(dupes.items()))
            raise errors.DuplicateSlugError(slug, paths)

        return sorted((page for _, page in loaded), key=lambda p: p.order)


# == Streamlit adapter layer ==


class DocsUI:
    """Streamlit adapter to render the DocsRegistry."""

    def __init__(self, registry: DocsRegistry) -> None:
        """Construct the DocsUI."""
        self.registry = registry

    def _render_page(self, doc: MarkdownPage) -> None:
        """Render a doc's body, translating any render-time failure.

        Raises:
            errors.PageRenderError: rendering the markdown body failed; carries
                the doc's slug and the original exception as the cause.

        """
        try:
            st.markdown(doc.content)
        except Exception as exc:
            raise errors.PageRenderError(doc.slug, exc) from exc

    def _to_streamlit_page(self, doc: MarkdownPage) -> "st_page.StreamlitPage":
        def _render() -> None:
            self._render_page(doc)

        return st.Page(
            _render,
            title=doc.title,
            icon=doc.icon,
            url_path=doc.slug,
        )

    def build_pages(self) -> list["st_page.StreamlitPage"]:
        """Build the StreamlitPage items for all registered docs."""
        return [self._to_streamlit_page(page) for page in self.registry.pages]
