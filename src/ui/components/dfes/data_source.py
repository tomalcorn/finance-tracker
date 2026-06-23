"""The read seam a DFE depends on, defined by the UI that consumes it.

A ``GridDataSource`` is the narrow port a dataframe editor needs from the
persistence layer: read the rows to display, and read the existing values of
a column (for uniqueness suffixing and filter widgets). The concrete
implementation is built in the composition layer over a repository and
injected via ``DFEConfig`` — keeping the UI decoupled from the repository
port surface.
"""

import typing


@typing.runtime_checkable
class GridDataSource(typing.Protocol):
    """The reads a DFE needs from persistence, scoped to the current user."""

    def load(self) -> list[dict]:
        """Return all rows to display in the editor (Path A: fetch-all)."""
        ...

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        ...
