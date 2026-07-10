"""The read/write seam a DFE depends on, defined by the UI that consumes it.

A ``GridDataSource`` is the narrow port a dataframe editor needs from the
persistence layer: read the rows to display (as typed view read models), read
the existing values of a column (for uniqueness suffixing and filter widgets),
and apply a batch of edits back. The concrete implementation is built in the
composition layer over a repository and injected via ``DFEConfig`` — keeping
the UI decoupled from the repository port surface.
"""

import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    import pydantic

    from domain import entities


@typing.runtime_checkable
class GridDataSource(typing.Protocol):
    """The reads and writes a DFE needs, scoped to the current user."""

    def rows(self) -> "Sequence[pydantic.BaseModel]":
        """Return all rows to display, as typed view models.

        Each row is a frozen ``domain.read_models`` view model carrying the
        SQL view's computed columns, so the grid receives typed values rather
        than bare dicts. Covariant (``Sequence``) so an implementation may
        return a concretely-typed ``list`` of one view model.
        """
        ...

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        ...

    def apply(self, updates: "entities.BackendUpdates") -> None:
        """Persist a batch of added, edited, and deleted rows.

        The grid speaks display rows and DataFrame deltas; the concrete
        implementation bridges those to the repository's write model and
        invalidates the reads the write affects. Computed view columns are
        never written back — the writable table has no such fields.
        """
        ...
