"""The query side of persistence: one aggregate's rows as typed view models.

``Repository`` is the write contract, and its reads return entities — the
writable table's columns only. A caller that needs a view's *computed* columns
(``current_balance``, ``remaining``, …) needs the read model instead, so it
depends on this port rather than widening ``Repository`` with a second type
parameter every write-side caller would have to carry.

Deliberately one method: a reader that needs a filtered read gets an explicit,
named method here, never a generic "pass any filter" argument.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pydantic


class ViewSource[ViewT: "pydantic.BaseModel"](Protocol):
    """Read one aggregate's display rows, scoped to the current user."""

    def rows(self) -> "Sequence[ViewT]":
        """Return all rows the caller may see, as typed view read models.

        Each row is a frozen ``domain.read_models`` view model carrying the SQL
        view's computed columns. Covariant (``Sequence``) so an implementation
        may return a concretely-typed ``list`` of one view model.
        """
        ...
