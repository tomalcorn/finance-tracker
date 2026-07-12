"""Custom errors for pages."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib


class DocsError(Exception):
    """Base for all docs-subsystem errors."""


class InvalidFrontmatterError(DocsError):
    """A markdown file has malformed or missing frontmatter values."""

    def __init__(self, path: "pathlib.Path", field: str, reason: str) -> None:
        """Construct InvalidFrontmatterError."""
        self.path = path
        self.field = field
        self.reason = reason
        super().__init__(f"{path.name}: invalid frontmatter field '{field}' — {reason}")


class MissingIconError(InvalidFrontmatterError):
    """Convenience subclass for the common missing-icon case."""

    def __init__(self, path: "pathlib.Path") -> None:
        """Construct MissingIconError."""
        super().__init__(path, field="icon", reason="must be a non-empty string")


class EmptyDocBodyError(DocsError):
    """A markdown file has no body content to derive a title from."""

    def __init__(self, path: "pathlib.Path") -> None:
        """Construct EmptyDocBodyError."""
        self.path = path
        super().__init__(f"{path.name}: file has no body content")


class DocReadError(DocsError):
    """A markdown file could not be read from disk."""

    def __init__(self, path: "pathlib.Path", cause: Exception) -> None:
        """Construct DocReadError."""
        self.path = path
        self.cause = cause
        super().__init__(f"{path.name}: could not read file — {cause}")


class DocsDirectoryError(DocsError):
    """The docs directory is absent or unreadable."""

    def __init__(self, docs_dir: "pathlib.Path") -> None:
        """Construct DocsDirectoryError."""
        self.docs_dir = docs_dir
        super().__init__(f"Docs directory not found: {docs_dir}")


class EmptyDocsDirectoryError(DocsError):
    """The docs directory exists but contains no markdown files."""

    def __init__(self, docs_dir: "pathlib.Path") -> None:
        """Construct EmptyDocsDirectoryError."""
        self.docs_dir = docs_dir
        super().__init__(f"No markdown files found in: {docs_dir}")


class DuplicateSlugError(DocsError):
    """Two docs resolved to the same slug."""

    def __init__(self, slug: str, paths: list["pathlib.Path"]) -> None:
        """Construct DuplicateSlugError."""
        self.slug = slug
        self.paths = paths
        names = ", ".join(p.name for p in paths)
        super().__init__(f"Duplicate slug '{slug}' produced by: {names}")


class PageRenderError(DocsError):
    """Wraps an unexpected error that occurs while rendering a Streamlit page."""

    def __init__(self, slug: str, cause: Exception) -> None:
        """Construct PageRenderError."""
        self.slug = slug
        self.cause = cause
        super().__init__(f"Failed to render page '{slug}': {cause}")
