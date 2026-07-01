"""The read seam a DFE depends on, defined by the UI that consumes it.

A ``GridDataSource`` is the narrow port a dataframe editor needs from the
persistence layer: read the rows to display (as typed view read models), and
read the existing values of a column (for uniqueness suffixing and filter
widgets). The concrete implementation is built in the composition layer over a
repository and injected via ``DFEConfig`` — keeping the UI decoupled from the
repository port surface.
"""

import typing

if typing.TYPE_CHECKING:
    import pydantic


@typing.runtime_checkable
class GridDataSource(typing.Protocol):
    """The reads a DFE needs from persistence, scoped to the current user."""

    def rows(self) -> "list[pydantic.BaseModel]":
        """Return all rows to display, as typed view models (Path A: fetch-all).

        Each row is a frozen ``domain.read_models`` view model carrying the
        SQL view's computed columns, so the grid receives typed values rather
        than bare dicts.
        """
        ...

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        ...
