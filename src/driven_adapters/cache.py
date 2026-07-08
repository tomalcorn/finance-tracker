"""Cache gateway abstraction for repository reads and writes.

The Supabase repositories depend on this Protocol, not on Streamlit. The
concrete implementation lives in the ui layer (a driving adapter) and is
injected at composition time. This keeps st.cache_data and session-state
versioning out of adapters/ while still letting repository reads and writes
participate in one coherent cache.

Reads and writes are two halves of one component: every write must invalidate
the reads it affects, so they live behind a single port rather than two
unrelated callables.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from domain import entities


class CacheGateway(Protocol):
    """Read-through cache plus write-with-invalidation for one backend.

    Implementations bind a connection at construction time, so callers pass
    only table names and updates. A write is responsible for invalidating
    every cached read it affects.
    """

    def fetch(self, table: str) -> list[dict]:
        """Return all rows for the table, served from cache when warm."""
        ...

    def write(self, table: str, updates: "entities.BackendUpdates") -> None:
        """Apply updates to the backend and invalidate affected cached reads."""
        ...
