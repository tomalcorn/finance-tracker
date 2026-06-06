"""Custom errors for pages."""

import pathlib


class MissingIconError(Exception):
    """Error from a doc missing an icon in the frontmatter."""

    def __init__(self, path: pathlib.Path) -> None:
        """Construct MissingIconError."""
        msg = (
            f"The following doc file has not defined an icon in its frontmatter: {path}"
        )
        super().__init__(msg)
