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
    def save(self, item: EntityT) -> None:
        """Insert or update a single record."""

    @abc.abstractmethod
    def apply(self, updates: "entities.BackendUpdates") -> None:
        """Apply a batch of inserts, edits, and deletes in one operation.

        A no-op batch is skipped so an unchanged grid never touches the backend.
        """
