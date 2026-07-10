"""Streamlit cache mechanism backing the repository cache gateway.

This module is the single source of truth for cached reads in the app:
  - a versioned @st.cache_data layer keyed by (table, query, version)
  - per-table version counters in session state used to bust the cache
  - invalidation helpers, including the views affected by a write

The repository CacheGateway (composition.cache) sits on these primitives, so a
repository write invalidates every cached read it affects. Nothing here is
repo-specific; it is pure Streamlit cache plumbing.
"""

import logging

import pydantic
import st_supabase_connection
import streamlit as st

from driven_adapters.supabase import client
from driven_adapters.supabase import table_names as adapter_table_names

logger = logging.getLogger(__name__)

JsonDict = dict[str, pydantic.JsonValue]

_TABLE_VERSIONS_KEY = "_cache_table_versions"


def get_connection() -> st_supabase_connection.SupabaseConnection:
    """Return the shared Supabase connection for this Streamlit session."""
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def _get_table_versions() -> dict[str, int]:
    """Get the table versions dict from session state, creating if needed."""
    if _TABLE_VERSIONS_KEY not in st.session_state:
        st.session_state[_TABLE_VERSIONS_KEY] = {}
    return st.session_state[_TABLE_VERSIONS_KEY]


@st.cache_data(ttl=300)
def _get_data_cached(
    table_name: str,
    query_string: str,
    table_version: int,
    _connection: st_supabase_connection.SupabaseConnection | None = None,
) -> list[JsonDict]:
    """Fetch all rows for a table from Supabase, memoised per (table, version).

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        table_version: Monotonically increasing version used to bust the cache
            for all queries on a given table via `invalidate_table_cache`.
        _connection: The Supabase connection to use.

    Returns:
        A list of dictionaries representing the queried data.

    """
    logger.info(
        "Cache miss — fetching from Supabase: table=%r query=%r version=%d",
        table_name,
        query_string,
        table_version,
    )
    connection = _connection or get_connection()
    return client.fetch_table(table_name, query_string, connection)


def fetch(
    table_name: str,
    query_string: str,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> list[JsonDict]:
    """Fetch rows for a table through the versioned cache.

    Args:
        table_name: The table or view to read.
        query_string: The select query string (usually "*").
        connection: The Supabase connection; falls back to the session
            connection when omitted.

    Returns:
        A list of row dicts, served from cache when warm.

    """
    version = _get_table_versions().get(table_name, 0)
    logger.info(
        "Cache lookup: table=%r query=%r version=%d",
        table_name,
        query_string,
        version,
    )
    return _get_data_cached(table_name, query_string, version, connection)


def invalidate_table_cache(table_name: str) -> None:
    """Invalidate all cached reads for the given table by bumping its version."""
    table_versions = _get_table_versions()
    new_version = table_versions.get(table_name, 0) + 1
    table_versions[table_name] = new_version
    logger.info(
        "Cache invalidated: table=%r new version=%d",
        table_name,
        new_version,
    )


def invalidate_with_affected_views(table_name: str) -> None:
    """Invalidate the written table and all views that depend on it."""
    invalidate_table_cache(table_name)
    try:
        key = adapter_table_names.TableNames(table_name)
    except ValueError:
        return
    for view in adapter_table_names.VIEWS_AFFECTED_BY.get(key, []):
        invalidate_table_cache(str(view))
