"""Module for handling interactions with Supabase backend."""

import logging
import typing

import pandas as pd
import pydantic
import st_supabase_connection  # type: ignore[import-untyped]
import streamlit as st
import supabase_auth

from libs import ss_keys
from libs.buttons import constants
from libs.dfes import constants as dfe_constants
from libs.models import backend_updates_model, frontend_models

CONN = st.connection("supabase", type=st_supabase_connection.SupabaseConnection)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


JsonDict = dict[str, pydantic.JsonValue]


def _ensure_authenticated() -> None:
    """Ensure the user is authenticated and the connection has a valid token."""
    # Check if we already have a valid session
    if ss_keys.SSKeys.CURRENT_USER in st.session_state:
        return

    email_password_creds = supabase_auth.SignInWithEmailAndPasswordCredentials(
        email="tomalcorn777@icloud.com",
        password="REDACTED",  # noqa: S106
    )

    with st.spinner("Signing in..."):
        auth_resp = CONN.auth.sign_in_with_password(email_password_creds)

        access_token = None
        user = None

        # Support multiple response shapes (object or dict)
        if hasattr(auth_resp, "session") and auth_resp.session:
            access_token = auth_resp.session.access_token
            user = auth_resp.user

        if not access_token:
            st.error("Authentication failed. Please check your credentials.")
            st.stop()

        CONN.client.postgrest.auth(access_token)
        st.session_state[ss_keys.SSKeys.CURRENT_USER] = user


class DataClientError(Exception):
    """Custom exception for data client errors."""

    def __init__(self, message: str) -> None:
        """Initialize DataClientError with a message."""
        super().__init__(message)
        self.message = message


def _execute_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
) -> list[JsonDict]:
    """Execute the given query and return the data."""
    response = query.execute()
    return typing.cast("list[JsonDict]", response.data or [])


def _apply_filters_to_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
    column_name: str,
    filters: frontend_models.Filters | None,
) -> st_supabase_connection.SyncSelectRequestBuilder:
    """Apply filters from column configurations to the query."""
    if filters is not None:
        for operator, criteria in filters.model_dump(exclude_none=True).items():
            if operator == "in":
                query = query.in_(column_name, criteria)
            else:
                query = query.filter(column_name, operator, criteria)
    return query


def _apply_sorting_to_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
    column_name: str,
    sorting: constants.SortingValues | None,
) -> st_supabase_connection.SyncSelectRequestBuilder:
    """Apply sorting from column configurations to the query."""
    if sorting is not None:
        query = query.order(
            column_name,
            desc=sorting == constants.SortingValues.DESC,
        )
    return query


_table_versions: dict[str, int] = {}


@st.cache_data(ttl=300)
def _get_data_cached(
    table_name: str,
    query_string: str,
    table_version: int,
    _configs: list[frontend_models.DFEColumnConfigBase] | None = None,
    _connection: st_supabase_connection.SupabaseConnection = CONN,
) -> list[JsonDict]:
    """Fetch data from the specified table with optional filters.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        table_version: Monotonically increasing version used to bust the cache
            for all queries on a given table via `invalidate_table_cache`.
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
    if _connection is CONN:
        _ensure_authenticated()

    query = _connection.table(table_name).select(query_string)
    if _configs:
        for config in _configs:
            query = _apply_filters_to_query(
                query=query,
                column_name=config.column_name,
                filters=config.filters,
            )
            query = _apply_sorting_to_query(
                query,
                column_name=config.column_name,
                sorting=config.sorting,
            )
    return _execute_query(query)


def get_data(
    table_name: str,
    query_string: str,
    _configs: list[frontend_models.DFEColumnConfigBase] | None = None,
    _connection: st_supabase_connection.SupabaseConnection = CONN,
) -> list[JsonDict]:
    """Fetch data from the specified table, routing through the versioned cache."""
    version = _table_versions.get(table_name, 0)
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
        _configs,
        _connection,
    )


def invalidate_table_cache(table_name: str) -> None:
    """Invalidate all cached `get_data` results for the given table."""
    new_version = _table_versions.get(table_name, 0) + 1
    _table_versions[table_name] = new_version
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
    connection: st_supabase_connection.SupabaseConnection = CONN,
) -> pd.Series:
    """Get all values in a column by executing a select query.

    Args:
        table_name: The name of the table to query.
        column_name: The name of the column to retrieve values from.
        unique: Whether to return only unique values.
        connection: The Supabase connection to use.

    Returns:
        A pandas Series containing the column values.

    """
    if connection is CONN:
        _ensure_authenticated()

    query = connection.table(table_name).select(column_name)
    response = _execute_query(query)
    if not response:
        return pd.Series()
    all_col_values = pd.Series(
        [row[column_name] for row in response if column_name in row],
    ).dropna()
    if unique:
        return all_col_values.drop_duplicates().reset_index(drop=True)
    return all_col_values.reset_index(drop=True)


def commit(
    table_name: str,
    tables_to_clear: list[dfe_constants.TableNames],
    connection: st_supabase_connection.SupabaseConnection = CONN,
) -> None:
    """Apply any pending sync updates for a table and clear them.

    Reads the BackendUpdates written by DFE.sync() from session state,
    applies them to the database, then removes them from session state.

    Args:
        table_name: The table whose pending updates should be applied.
        tables_to_clear: Tables whose cached working_df should be invalidated.
        connection: The Supabase connection to use.

    """
    backend_updates_key = f"{table_name}_{ss_keys.SSKeys.BACKEND_UPDATES}"
    updates = st.session_state.pop(
        backend_updates_key,
        backend_updates_model.BackendUpdates(),
    )
    update_backend(table_name, updates, tables_to_clear, connection)


def update_backend(
    table_name: str,
    updates: backend_updates_model.BackendUpdates,
    tables_to_clear: list[dfe_constants.TableNames] | None = None,
    connection: st_supabase_connection.SupabaseConnection = CONN,
) -> backend_updates_model.BackendUpdates:
    """Update the backend with the provided changes.

    Args:
        table_name: The name of the table to update.
        updates: The BackendUpdates object containing added, edited, and deleted rows.
        tables_to_clear: List of tables to clear from the cache.
        connection: The Supabase connection to use.

    Returns:
        The updated BackendUpdates object reflecting all changes made.

    """
    if connection is CONN:
        _ensure_authenticated()

    update_made = False
    if updates.added_rows:
        connection.table(table_name).insert(updates.added_rows).execute()
        update_made = True

    if updates.edited_rows:
        for row_id, changes in updates.edited_rows.items():
            connection.table(table_name).update(changes).eq("id", row_id).execute()
        update_made = True
    if updates.deleted_rows:
        connection.table(table_name).delete().in_(
            "id",
            updates.deleted_rows,
        ).execute()
        updates.deleted_rows.clear()
        update_made = True

    if update_made:
        invalidate_table_cache(table_name)
        for t in tables_to_clear or []:
            invalidate_table_cache(t.value)
            working_df_key = f"{t.value}_{ss_keys.SSKeys.WORKING_DF}"
            if working_df_key in st.session_state:
                del st.session_state[working_df_key]

    return updates
