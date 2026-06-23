"""Concrete GridDataSource built over a Supabase repository.

Lives in the composition layer because it is the seam where a UI component's
read port (``ui.components.dfes.data_source.GridDataSource``) is satisfied by
a concrete adapter. Both reads are user-scoped by the repository.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adapters.supabase import repository as supabase_repos


class RepositoryGridDataSource:
    """Adapt a Supabase repository to the GridDataSource port."""

    def __init__(self, repository: "supabase_repos.SupabaseRepositoryBase") -> None:
        """Wrap the repository whose rows this data source reads."""
        self._repository = repository

    def load(self) -> list[dict]:
        """Return all rows to display, raw from the read view (Path A)."""
        return self._repository.get_rows()

    def unique_values(self, column_name: str) -> set[object]:
        """Return the set of existing values for a column."""
        return self._repository.get_column_values(column_name)
