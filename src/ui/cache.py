"""Streamlit cache mechanism backing the repository cache gateway.

This module is the single source of truth for cached reads in the app:
  - a versioned @st.cache_data layer keyed by (table, query, version, filter)
  - per-table version counters in session state used to bust the cache
  - invalidation helpers, including the views affected by a write

The repository CacheGateway (composition.cache) sits on these primitives, so a
repository write invalidates every cached read it affects. Nothing here is
repo-specific; it is pure Streamlit cache plumbing.
"""

import logging
from typing import TYPE_CHECKING

import pydantic
import st_supabase_connection
import streamlit as st

from adapters.supabase import client
from adapters.supabase import table_names as adapter_table_names
from domain import query as query_mod
from ui import ss_keys

if TYPE_CHECKING:
    from ui.models import frontend_models

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
    filter_key: str = "",  # noqa: ARG001 - used by @st.cache_data as a cache key
    _configs: list["frontend_models.DFEColumnConfigBase"] | None = None,
    _connection: st_supabase_connection.SupabaseConnection | None = None,
) -> list[JsonDict]:
    """Fetch data from the specified table with optional filters.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        table_version: Monotonically increasing version used to bust the cache
            for all queries on a given table via `invalidate_table_cache`.
        filter_key: Hashable string that differentiates queries with different
            filter/sort configs on the same table.
        _configs: Optional list of column configurations for filtering and sorting.
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
    column_queries = [
        query_mod.ColumnQuery(
            column_name=c.column_name,
            filters=c.filters,
            sorting_direction=c.sorting,
        )
        for c in (_configs or [])
    ]
    return client.fetch_table(table_name, query_string, column_queries, connection)


def _build_filter_key(
    configs: list["frontend_models.DFEColumnConfigBase"] | None,
) -> str:
    """Build a hashable cache key from filter/sort configs."""
    if not configs:
        return ""
    parts: list[str] = []
    for c in configs:
        if c.filters:
            parts.append(f"{c.column_name}:{c.filters.model_dump_json()}")
        if c.sorting:
            parts.append(f"{c.column_name}:sort={c.sorting}")
    return "|".join(parts)


def fetch(
    table_name: str,
    query_string: str,
    configs: list["frontend_models.DFEColumnConfigBase"] | None = None,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> list[JsonDict]:
    """Fetch rows for a table through the versioned cache.

    Args:
        table_name: The table or view to read.
        query_string: The select query string (usually "*").
        configs: Optional DFE column configs for filtered/sorted reads.
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
    return _get_data_cached(
        table_name,
        query_string,
        version,
        _build_filter_key(configs),
        configs,
        connection,
    )


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


def _invalidate_cache_and_working_df(name: str) -> None:
    """Invalidate the fetch cache and remove any cached working DataFrame."""
    invalidate_table_cache(name)
    working_df_key = f"{name}_{ss_keys.SSKeys.WORKING_DF}"
    if working_df_key in st.session_state:
        del st.session_state[working_df_key]


def invalidate_with_affected_views(table_name: str) -> None:
    """Invalidate the written table and all views that depend on it."""
    _invalidate_cache_and_working_df(table_name)
    try:
        key = adapter_table_names.TableNames(table_name)
    except ValueError:
        return
    for view in adapter_table_names.VIEWS_AFFECTED_BY.get(key, []):
        _invalidate_cache_and_working_df(str(view))
