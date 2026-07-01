"""Adapt a repository to the UI's ``GridDataSource`` read/write port.

``rows()`` maps the repository's raw user-scoped view rows into the aggregate's
frozen ``domain.read_models`` view model; ``unique_values()`` passes through;
``apply()`` hands a batch of grid deltas to the repository, which writes them
and invalidates the affected reads. All operations are user-scoped by the
repository.
"""

import typing

if typing.TYPE_CHECKING:
    import pydantic

    from domain import entities


class _GridRepository(typing.Protocol):
    """The reads and write RepositoryGridDataSource needs from a repository."""

    def get_rows(self) -> list[dict]:
        """Return the raw user-scoped rows from the read view."""
        ...

    def get_column_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        ...

    def apply_updates(self, updates: "entities.BackendUpdates") -> None:
        """Write a batch of inserts, edits, and deletes and invalidate reads."""
        ...


class RepositoryGridDataSource:
    """Adapt a Supabase repository to the GridDataSource port."""

    def __init__(
        self,
        repository: _GridRepository,
        view_model: "type[pydantic.BaseModel] | None" = None,
    ) -> None:
        """Wrap the repository whose rows this data source reads.

        Args:
            repository: The user-scoped repository to read from.
            view_model: The ``domain.read_models`` view model that raw rows are
                validated into by ``rows()``. ``None`` for aggregates with no
                view (payments), whose ``rows()`` is not yet wired.

        """
        self._repository = repository
        self._view_model = view_model

    def rows(self) -> "list[pydantic.BaseModel]":
        """Return all rows to display, as typed view models (Path A).

        Raises:
            RuntimeError: If this data source was built without a view model
                (e.g. payments), so no typed display read is available.

        """
        if self._view_model is None:
            msg = "This GridDataSource has no view model; rows() is unavailable."
            raise RuntimeError(msg)
        raw_rows = self._repository.get_rows()
        return [self._view_model.model_validate(row) for row in raw_rows]

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        return self._repository.get_column_values(column_name)

    def apply(self, changes: "entities.BackendUpdates") -> None:
        """Persist a batch of added, edited, and deleted rows.

        Delegates to the repository, which writes the deltas against its write
        model and invalidates the reads they affect. An empty batch is a no-op
        the repository skips.
        """
        self._repository.apply_updates(changes)
