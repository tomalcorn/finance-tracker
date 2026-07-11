"""Streamlit cache implementation backing the repository ``CacheGateway``.

A versioned ``@st.cache_data`` layer keyed by ``(key, version)`` with per-key
version counters in session state used to bust the cache. Keys are opaque
strings supplied by the repository; nothing here knows about Supabase tables,
views, or the client. Composition injects a ``StreamlitCache`` as the
driven-side ``CacheGateway``.
"""

import logging
from typing import TYPE_CHECKING

import st_supabase_connection
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)

_KEY_VERSIONS_KEY = "_cache_key_versions"


def get_connection() -> st_supabase_connection.SupabaseConnection:
    """Return the shared Supabase connection for this Streamlit session."""
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def _get_key_versions() -> dict[str, int]:
    """Return the per-key version dict from session state, creating if needed."""
    if _KEY_VERSIONS_KEY not in st.session_state:
        st.session_state[_KEY_VERSIONS_KEY] = {}
    return st.session_state[_KEY_VERSIONS_KEY]


@st.cache_data(ttl=300)
def _get_data_cached[T](
    key: str,
    version: int,
    _loader: "Callable[[], T]",
) -> T:
    """Return the loader's value, memoised per ``(key, version)``.

    ``_loader`` is underscore-prefixed so ``st.cache_data`` does not try to hash
    it; the ``(key, version)`` pair is the whole cache identity. A bumped version
    misses the cache and re-runs the loader.

    Args:
        key: The opaque cache key identifying this read.
        version: Monotonically increasing version bumped by ``invalidate`` to
            bust the cache for ``key``.
        _loader: Callable that fetches the value on a cache miss.

    Returns:
        The loader's value, served from cache when warm.

    """
    logger.info("Cache miss — loading: key=%r version=%d", key, version)
    return _loader()


class StreamlitCache:
    """``CacheGateway`` backed by ``st.cache_data`` + per-key session versions."""

    def get_or_load[T](
        self,
        key: str,
        loader: "Callable[[], T]",
    ) -> T:
        """Return cached value for ``key``, running ``loader`` on a miss."""
        version = _get_key_versions().get(key, 0)
        logger.info("Cache lookup: key=%r version=%d", key, version)
        return _get_data_cached(key, version, loader)

    def invalidate(self, keys: "Iterable[str]") -> None:
        """Bump each key's version, busting its cached rows."""
        versions = _get_key_versions()
        for key in keys:
            versions[key] = versions.get(key, 0) + 1
            logger.info("Cache invalidated: key=%r new version=%d", key, versions[key])
