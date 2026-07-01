"""Concrete GridDataSource built over a Supabase repository.

Lives in the composition layer because it is the seam where a UI component's
read port (``ui.components.dfes.data_source.GridDataSource``) is satisfied by
a concrete adapter. Both reads are user-scoped by the repository.

``rows()`` maps the repository's raw user-scoped view rows into the aggregate's
frozen ``domain.read_models`` view model. This is where the typed read *is* the
view — the ``get_all()``-drops-computed-columns footgun cannot recur here
because the computed columns are declared on the read model.
"""

import typing

if typing.TYPE_CHECKING:
    import pydantic


class _RepositoryReads(typing.Protocol):
    """The two reads RepositoryGridDataSource needs from a repository."""

    def get_rows(self) -> list[dict]:
        """Return the raw user-scoped rows from the read view."""
        ...

    def get_column_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        ...


class RepositoryGridDataSource:
    """Adapt a Supabase repository to the GridDataSource port."""

    def __init__(
        self,
        repository: _RepositoryReads,
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
