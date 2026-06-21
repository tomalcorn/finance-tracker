"""Streamlit cache management for Supabase reads and writes.

All raw I/O is handled by adapters.supabase.client. This module owns:
  - the versioned @st.cache_data layer for reads
  - cache invalidation (by table and affected views)
  - a commit helper that flushes DFE session-state updates
  - make_repo_fetch_fn, which threads the cache into repository reads
"""

import collections.abc
import logging

import pandas as pd
import pydantic
import st_supabase_connection
import streamlit as st

from adapters.supabase import client
from adapters.supabase import table_names as adapter_table_names
from domain import entities
from domain import query as query_mod
from ui import ss_keys
from ui.models import frontend_models

logger = logging.getLogger(__name__)

JsonDict = dict[str, pydantic.JsonValue]


def _get_connection() -> st_supabase_connection.SupabaseConnection:
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


_TABLE_VERSIONS_KEY = "_data_client_table_versions"


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
    _configs: list[frontend_models.DFEColumnConfigBase] | None = None,
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
    connection = _connection or _get_connection()
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
    configs: list[frontend_models.DFEColumnConfigBase] | None,
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


def get_data(
    table_name: str,
    query_string: str,
    _configs: list[frontend_models.DFEColumnConfigBase] | None = None,
    _connection: st_supabase_connection.SupabaseConnection | None = None,
) -> list[JsonDict]:
    """Fetch data from the specified table, routing through the versioned cache."""
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
        _build_filter_key(_configs),
        _configs,
        _connection,
    )


def invalidate_table_cache(table_name: str) -> None:
    """Invalidate all cached `get_data` results for the given table."""
    table_versions = _get_table_versions()
    new_version = table_versions.get(table_name, 0) + 1
    table_versions[table_name] = new_version
    logger.info(
        "Cache invalidated: table=%r new version=%d",
        table_name,
        new_version,
    )


def get_column_values(
    table_name: str,
    column_name: str,
    *,
    unique: bool = False,
    connection: st_supabase_connection.SupabaseConnection | None = None,
) -> pd.Series:
    """Get all values in a column, delegating to the adapter layer."""
    return client.get_column_values(
        table_name,
        column_name,
        unique=unique,
        connection=connection or _get_connection(),
    )


def commit(
    table_name: str,
    connection: st_supabase_connection.SupabaseConnection | None = None,
    key_prefix: str | None = None,
) -> None:
    """Apply any pending sync updates for a table and clear them.

    Reads the BackendUpdates written by DFE.sync() from session state,
    applies them to the database, then removes them from session state.

    Args:
        table_name: The table whose pending updates should be applied.
        connection: The Supabase connection to use.
        key_prefix: The session state key prefix. Defaults to table_name.

    """
    prefix = key_prefix or table_name
    backend_updates_key = f"{prefix}_{ss_keys.SSKeys.BACKEND_UPDATES}"
    updates = st.session_state.pop(
        backend_updates_key,
        entities.BackendUpdates(),
    )
    update_backend(table_name, updates, connection)


def update_backend(
    table_name: str,
    updates: entities.BackendUpdates,
    connection: st_supabase_connection.SupabaseConnection | None = None,
    tables_to_clear: list[str] | None = None,
) -> entities.BackendUpdates:
    """Write updates to the backend and invalidate affected caches.

    Args:
        table_name: The name of the table to update.
        updates: The BackendUpdates object containing added, edited, and deleted rows.
        connection: The Supabase connection to use.
        tables_to_clear: Extra names to invalidate beyond those derived from
            VIEWS_AFFECTED_BY. Retained for base_dfe compatibility.

    Returns:
        The updated BackendUpdates object reflecting all changes made.

    """
    had_changes = bool(
        updates.added_rows or updates.edited_rows or updates.deleted_rows,
    )
    client.update_backend(table_name, updates, connection or _get_connection())
    if had_changes:
        _invalidate_with_affected_views(table_name)
        for t in tables_to_clear or []:
            _invalidate_cache_and_working_df(t)
    return updates


def _invalidate_cache_and_working_df(name: str) -> None:
    """Invalidate the fetch cache and remove any cached working DataFrame."""
    invalidate_table_cache(name)
    working_df_key = f"{name}_{ss_keys.SSKeys.WORKING_DF}"
    if working_df_key in st.session_state:
        del st.session_state[working_df_key]


def _invalidate_with_affected_views(table_name: str) -> None:
    """Invalidate the written table and all views that depend on it."""
    _invalidate_cache_and_working_df(table_name)
    try:
        key = adapter_table_names.TableNames(table_name)
    except ValueError:
        return
    for view in adapter_table_names.VIEWS_AFFECTED_BY.get(key, []):
        _invalidate_cache_and_working_df(str(view))


def make_repo_fetch_fn(
    connection: st_supabase_connection.SupabaseConnection,
) -> collections.abc.Callable:
    """Return a cached fetch function suitable for injecting into repositories.

    The returned function wraps _get_data_cached with a version lookup so
    repository reads participate in the same cache-busting mechanism as DFE reads.
    """
    def _fetch(
        table_name: str,
        query_string: str,
        _column_queries: list,
        _conn: st_supabase_connection.SupabaseConnection,
    ) -> list[JsonDict]:
        version = _get_table_versions().get(str(table_name), 0)
        return _get_data_cached(table_name, query_string, version, "", None, connection)

    return _fetch
