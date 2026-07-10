"""Streamlit-backed cache wiring for repository reads and writes.

Lives in composition because it knows Streamlit caching specifics and the
concrete Supabase client — neither of which the inner layers may depend on.
Builds the CacheGateway that wiring injects into repositories, and exposes the
session connection. Both the gateway and the DFE facade sit on the shared
driving_adapters.cache primitives, so repository reads and DFE reads share one
coherent cache.
"""

from typing import TYPE_CHECKING

from driven_adapters.supabase import client
from driving_adapters import cache as ui_cache

if TYPE_CHECKING:
    import st_supabase_connection

    from domain import entities

JsonDict = ui_cache.JsonDict


class StreamlitCacheGateway:
    """CacheGateway (see driven_adapters.cache) backed by driving_adapters.cache.

    Reads go through the versioned @st.cache_data layer; writes hit Supabase
    and then bump the table version (plus dependent view versions), so a
    repository write can never leave a stale cached read behind.
    """

    def __init__(self, connection: "st_supabase_connection.SupabaseConnection") -> None:
        """Bind the gateway to a Supabase connection for this session."""
        self._connection = connection

    def fetch(self, table: str) -> list[JsonDict]:
        """Return all rows for the table, served from the versioned cache."""
        return ui_cache.fetch(table, "*", self._connection)

    def write(self, table: str, updates: "entities.BackendUpdates") -> None:
        """Apply updates to Supabase and invalidate affected cached reads."""
        table_name = str(table)
        had_changes = bool(
            updates.added_rows or updates.edited_rows or updates.deleted_rows,
        )
        client.update_backend(table_name, updates, self._connection)
        if had_changes:
            ui_cache.invalidate_with_affected_views(table_name)


def make_cache_gateway(
    connection: "st_supabase_connection.SupabaseConnection",
) -> StreamlitCacheGateway:
    """Return a Streamlit-backed CacheGateway for injecting into repositories."""
    return StreamlitCacheGateway(connection)
