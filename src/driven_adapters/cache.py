"""Cache gateway abstraction for repository reads.

The Supabase repositories depend on this Protocol, not on Streamlit. The
concrete implementation lives in the driving-adapters (UI) layer and is injected
at composition time, keeping ``st.cache_data`` and session-state versioning out
of ``driven_adapters/``.

The gateway caches opaque string keys against loader callables. The repository
owns key construction (user-scoped ``{user_id}:{table}``) and the
invalidation fan-out (a written table plus the views that depend on it), so the
gateway carries no Supabase schema knowledge and no write path.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


class CacheGateway(Protocol):
    """Read-through cache keyed by opaque strings."""

    def get_or_load[T](
        self,
        key: str,
        loader: "Callable[[], T]",
    ) -> T:
        """Return the cached value for ``key``, calling ``loader`` on a miss."""
        ...

    def invalidate(self, keys: "Iterable[str]") -> None:
        """Bust the cache for each of the given keys."""
        ...
