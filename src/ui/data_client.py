"""DFE-facing data access: cached reads, commits, and write invalidation.

A thin facade over ui.cache (the shared Streamlit cache mechanism) for the
data-frame-editor (DFE) components. Repository reads/writes use
composition.cache instead; both sit on the same ui.cache primitives so their
caches stay coherent.
"""

from typing import TYPE_CHECKING

import pydantic
import streamlit as st

from adapters.supabase import client
from domain import entities
from ui import cache, ss_keys

if TYPE_CHECKING:
    import pandas as pd
    import st_supabase_connection

    from ui.models import frontend_models

JsonDict = dict[str, pydantic.JsonValue]


def get_data(
    table_name: str,
    query_string: str,
    _configs: list["frontend_models.DFEColumnConfigBase"] | None = None,
    _connection: "st_supabase_connection.SupabaseConnection | None" = None,
) -> list[JsonDict]:
    """Fetch data for the table through the shared versioned cache."""
    return cache.fetch(table_name, query_string, _configs, _connection)


def invalidate_table_cache(table_name: str) -> None:
    """Invalidate all cached reads for the given table."""
    cache.invalidate_table_cache(table_name)


def get_column_values(
    table_name: str,
    column_name: str,
    *,
    unique: bool = False,
    connection: "st_supabase_connection.SupabaseConnection | None" = None,
) -> "pd.Series":
    """Get all values in a column, delegating to the adapter layer."""
    return client.get_column_values(
        table_name,
        column_name,
        unique=unique,
        connection=connection or cache.get_connection(),
    )


def commit(
    table_name: str,
    connection: "st_supabase_connection.SupabaseConnection | None" = None,
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
    connection: "st_supabase_connection.SupabaseConnection | None" = None,
) -> entities.BackendUpdates:
    """Write updates to the backend and invalidate affected caches.

    Args:
        table_name: The name of the table to update.
        updates: The BackendUpdates object containing added, edited, and deleted rows.
        connection: The Supabase connection to use.

    Returns:
        The updated BackendUpdates object reflecting all changes made.

    """
    had_changes = bool(
        updates.added_rows or updates.edited_rows or updates.deleted_rows,
    )
    client.update_backend(table_name, updates, connection or cache.get_connection())
    if had_changes:
        cache.invalidate_with_affected_views(table_name)
    return updates
