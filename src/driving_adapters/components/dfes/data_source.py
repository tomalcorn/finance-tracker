"""The read/write seam a DFE depends on, defined by the UI that consumes it.

A ``GridDataSource`` is the narrow port a dataframe editor needs from the
persistence layer: read the rows to display (as typed view read models), read
the existing values of a column (for uniqueness suffixing and filter widgets),
create rows through the entity gate, and patch or delete existing ones. The
concrete implementation is built in the composition layer over a repository and
injected via ``DFEConfig`` — keeping the UI decoupled from the repository port
surface.

Creation is deliberately two steps (``build_entities`` then ``save_entities``):
raw column values become a complete, correctly-owned entity before anything is
written, so the write path through the entity is visible at the call site rather
than hidden behind one method.
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

    def build_entities(
        self,
        rows: "Sequence[entities.RawRow]",
    ) -> "Sequence[typing.Any]":
        """Complete and validate raw rows into entities, without persisting.

        The grid collects user input as bare column values; the implementation
        completes each row with the ownership context it writes under and
        validates it, so a row the grid adds is a valid, correctly-owned entity
        before anything is written. The entity type is opaque to the grid — it
        only passes the result back to ``save_entities``.
        """
        ...

    def save_entities(self, items: "Sequence[typing.Any]") -> None:
        """Persist complete entities, inserting or updating each by id."""
        ...

    def apply_edits(self, edits: "entities.EditedRows") -> None:
        """Patch the given columns of stored rows, keyed by row id.

        Computed view columns are never written back — the writable table has no
        such fields.
        """
        ...

    def apply_deletions(self, ids: "entities.DeletedIds") -> None:
        """Delete the rows with the given ids."""
        ...
