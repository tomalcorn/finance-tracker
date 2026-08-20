"""The read/write seam a DFE depends on, defined by the UI that consumes it.

A ``GridDataSource`` is the narrow port a dataframe editor needs from the
persistence layer: read the rows to display (as typed view read models, via the
``ViewSource`` read port it extends), read the existing values of a column (for
uniqueness suffixing and filter widgets), create rows through the entity gate,
and patch or delete existing ones. The concrete implementation is built in the
composition layer over a repository and injected via ``DFEConfig`` — keeping the
UI decoupled from the repository port surface.

Generic over its view model, so a holder declares the rows it reads
(``GridDataSource[read_models.CategoryView]``) and gets them back typed. The
grid itself does not care, and holds ``GridDataSource[pydantic.BaseModel]``:
the parameter is covariant, so any concretely-typed source satisfies it.

Creation is deliberately two steps (``build_entities`` then ``save_entities``):
raw column values become a complete, correctly-owned entity before anything is
written, so the write path through the entity is visible at the call site rather
than hidden behind one method.
"""

import typing

from ports import views

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    import pydantic

    from domain import entities


@typing.runtime_checkable
class GridDataSource[ViewT: "pydantic.BaseModel"](
    views.ViewSource[ViewT],
    typing.Protocol,
):
    """The reads and writes a DFE needs, scoped to the current user.

    ``rows()`` comes from ``ViewSource``: the display read is the same query the
    summary use cases make, so the grid asks for it through the same port rather
    than redeclaring it.
    """

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
