"""Abstract repository port for all domain aggregates.

A single generic ``Repository[EntityT]`` defines what the application *needs*
from persistence, independent of any concrete backend. Use cases depend on it
parametrised by the aggregate they operate on (e.g.
``Repository[SubscriptionModel]``).
"""

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    import pydantic

    from domain import entities


class Repository[EntityT: "pydantic.BaseModel"](abc.ABC):
    """Port for persisting and reading a single aggregate type."""

    @abc.abstractmethod
    def get_all(self) -> list[EntityT]:
        """Return all records for the current user."""

    @abc.abstractmethod
    def get_by_ids(self, ids: list["uuid.UUID"]) -> list[EntityT]:
        """Return the records matching the given IDs.

        Order is not guaranteed to match ``ids``.
        """

    @abc.abstractmethod
    def build_entities(self, rows: "Sequence[entities.RawRow]") -> list[EntityT]:
        """Complete and validate raw rows into entities — the write gate.

        Each row is completed with the ownership context this repository writes
        under (its owner, ownership mode, and joint account where applicable)
        and then validated into an entity. Callers that hold only user-supplied
        fields go through here; a caller already holding every field may
        construct the entity directly. Nothing is persisted.

        Args:
            rows: Raw field maps, each missing the ownership context.

        Returns:
            One complete entity per input row, in the same order.

        Raises:
            RepositoryError: A row is not valid for this aggregate, or the
                ownership context could not be resolved.

        """

    @abc.abstractmethod
    def save_entities(self, items: "Sequence[EntityT]") -> None:
        """Persist complete entities, inserting or updating each by id.

        Every write of a whole row goes through here, whether the entity is new
        or a modified copy of a stored one. An empty list is a no-op.

        Raises:
            RepositoryError: The write failed, or an entity is not owned the way
                this repository writes.

        """

    @abc.abstractmethod
    def apply_edits(self, edits: "entities.EditedRows") -> None:
        """Patch the given columns of stored rows, keyed by row id.

        Partial by design: only the supplied columns change. Identity and
        ownership columns are not editable, so a patch cannot move a row between
        owners. An empty patch set is a no-op.

        Raises:
            RepositoryError: The write failed.

        """

    @abc.abstractmethod
    def apply_deletions(self, ids: "entities.DeletedIds") -> None:
        """Delete the rows with the given ids. An empty list is a no-op.

        Raises:
            RepositoryError: The write failed.

        """
