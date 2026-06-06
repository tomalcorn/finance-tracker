"""Helpers for building Streamlit docs pages from markdown files."""

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

    title: Annotated[str, pydantic.Field(description="Title of the Doc")]
    slug: SLUG
    order: Annotated[
        pydantic.PositiveInt,
        pydantic.Field(description="order of the doc for rendering in UI."),
    ]
    icon: Annotated[
        str,
        pydantic.Field(description="Optional Streamlit icon for the doc page."),
    ]
    content: Annotated[
        str,
        pydantic.Field(description="Content of the doc.", min_length=0),
    ]


# == Use Case ==


def load_markdown_doc(path: pathlib.Path) -> MarkdownPage:
    """Load a MarkdownPage from a md file."""
    raw = path.read_text(encoding="utf-8")

    metadata, body = _parse_frontmatter(raw)

    title = (
        metadata.get("front_matter_title") or body.splitlines()[0].lstrip("# ").strip()
    )
    slug = SLUG_ADAPTER.validate_python(metadata.get("slug") or title)
    order = int(metadata.get("order", 9999))
    icon = metadata.get("icon")

    if not isinstance(icon, str):
        raise errors.MissingIconError

    return MarkdownPage(
        title=title,
        slug=slug,
        order=order,
        icon=icon,
        content=body,
    )


class DocsRegistry:
    """Registry for docs."""

    def __init__(self, docs_dir: pathlib.Path) -> None:
        """Construct the DocsRegistry."""
        self._docs_dir = docs_dir

    @functools.cached_property
    def pages(self) -> list[MarkdownPage]:
        """List of pages for the DocsRegistry."""
        pages = [load_markdown_doc(path) for path in self._docs_dir.glob("*.md")]

        return sorted(pages, key=lambda p: p.order)


# == Streamlit adapter layer ==


class DocsUI:
    """Streamlit adapter to render the DocsRegistry."""

    def __init__(self, registry: DocsRegistry) -> None:
        """Construct the DocsUI."""
        self.registry = registry

    def _to_streamlit_page(self, doc: MarkdownPage) -> st_page.StreamlitPage:
        def _render() -> None:
            st.markdown(doc.content)

        return st.Page(
            _render,
            title=doc.title,
            icon=doc.icon,
            url_path=doc.slug,
        )

    def build_pages(self) -> list[st_page.StreamlitPage]:
        """Build the StreamlitPage items."""
        return [self._to_streamlit_page(page) for page in self.registry.pages]
