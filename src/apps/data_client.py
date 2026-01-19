"""Module for handling interactions with Supabase backend."""

import typing

import pandas as pd
import st_supabase_connection
import streamlit as st
import supabase_auth

from libs import constants, frontend_models

CONN = st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def _ensure_authenticated() -> None:
    """Ensure the user is authenticated and the connection has a valid token."""
    # Check if we already have a valid session
    if constants.SSKeys.CURRENT_USER in st.session_state:
        return

    email_password_creds = supabase_auth.SignInWithEmailAndPasswordCredentials(
        email="tomalcorn777@icloud.com",
        password="jiwQij-kirwi3-hedtyk",  # noqa: S106
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
        st.session_state[constants.SSKeys.CURRENT_USER] = user


# Authenticate on module load
_ensure_authenticated()


class DataClientError(Exception):
    """Custom exception for data client errors."""

    def __init__(self, message: str) -> None:
        """Initialize DataClientError with a message."""
        super().__init__(message)
        self.message = message


def _hash_func_for_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
) -> str:
    """Generate a hash for the given query to use in caching."""
    query_str = str(query)
    return str(hash(query_str))


@st.cache_data(
    ttl=300,
    hash_funcs={st_supabase_connection.SyncSelectRequestBuilder: _hash_func_for_query},
)
def _execute_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
) -> list[dict[str, typing.Any]]:
    """Execute the given query and return the data."""
    response = query.execute()
    return response.data or []


def _apply_filters_to_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
    column_name: str,
    filters: frontend_models.Filters | None,
) -> st_supabase_connection.SyncSelectRequestBuilder:
    """Apply filters from column configurations to the query."""
    if filters is not None:
        for operator, criteria in filters.model_dump(exclude_none=True).items():
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


def get_data(
    table_name: str,
    query_string: str,
    configs: list[frontend_models.DFEColumnConfig] | None = None,
    connection: st_supabase_connection.SupabaseConnection = CONN,
) -> list[dict[str, typing.Any]]:
    """Fetch data from the specified table with optional filters.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        configs: Optional list of column configurations for filtering and sorting.
        connection: The Supabase connection to use.

    Returns:
        A list of dictionaries representing the queried data.

    """
    query = connection.table(table_name).select(query_string)
    if configs:
        for config in configs:
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


def update_backend(
    table_name: str,
    updates: frontend_models.BackendUpdates,
    connection: st_supabase_connection.SupabaseConnection = CONN,
) -> frontend_models.BackendUpdates:
    """Update the backend with the provided changes.

    Args:
        table_name: The name of the table to update.
        updates: The BackendUpdates object containing added, edited, and deleted rows.
        connection: The Supabase connection to use.

    Returns:
        The updated BackendUpdates object reflecting all changes made.

    """
    if updates.added_rows:
        connection.table(table_name).insert(updates.added_rows).execute()
    if updates.edited_rows:
        for row_id, changes in updates.edited_rows.items():
            connection.table(table_name).update(changes).eq("id", row_id).execute()
    if updates.deleted_rows:
        connection.table(table_name).delete().in_(
            "id",
            updates.deleted_rows,
        ).execute()
        updates.deleted_rows.clear()

    return updates
