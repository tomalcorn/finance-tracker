"""Client to support reading/writing/updating to supabase."""

from typing import TYPE_CHECKING, cast

import pandas as pd
import pydantic

from domain import entities
from domain import query as query_mod

if TYPE_CHECKING:
    import st_supabase_connection

JsonDict = dict[str, pydantic.JsonValue]


def _execute_query(
    query: "st_supabase_connection.SyncSelectRequestBuilder",
) -> list[JsonDict]:
    """Execute the given query and return the data."""
    response = query.execute()
    return cast("list[JsonDict]", response.data or [])


def _apply_filters_to_query(
    query: "st_supabase_connection.SyncSelectRequestBuilder",
    column_name: str,
    filters: query_mod.Filters | None,
) -> "st_supabase_connection.SyncSelectRequestBuilder":
    """Apply filters from column configurations to the query."""
    if filters is not None:
        for operator, criteria in filters.model_dump(exclude_none=True).items():
            if operator == "in":
                query = query.in_(column_name, criteria)
            elif operator == "cs":
                query = query.filter(column_name, "cs", f"{{{criteria}}}")
            elif operator == "contains":
                query = query.ilike(column_name, f"%{criteria}%")
            else:
                query = query.filter(column_name, operator, criteria)
    return query


def _apply_sorting_to_query(
    query: "st_supabase_connection.SyncSelectRequestBuilder",
    column_name: str,
    sorting: query_mod.SortingValues | None,
) -> "st_supabase_connection.SyncSelectRequestBuilder":
    """Apply sorting from column configurations to the query."""
    if sorting is not None:
        query = query.order(
            column_name,
            desc=sorting == query_mod.SortingValues.DESC,
        )
    return query


def fetch_table(
    table_name: str,
    query_string: str,
    column_queries: list[query_mod.ColumnQuery],
    connection: "st_supabase_connection.SupabaseConnection",
) -> list[JsonDict]:
    """Fetch data from the specified table with optional filters.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        column_queries: configs to filter and sort the query.
        connection: connection object to query against.

    Returns:
        A list of dictionaries representing the queried data.

    """
    query = connection.table(table_name).select(query_string)
    if column_queries:
        for column_query in column_queries:
            query = _apply_filters_to_query(
                query=query,
                column_name=column_query.column_name,
                filters=column_query.filters,
            )
            query = _apply_sorting_to_query(
                query=query,
                column_name=column_query.column_name,
                sorting=column_query.sorting_direction,
            )
    return _execute_query(query)


def update_backend(
    table_name: str,
    updates: entities.BackendUpdates,
    connection: "st_supabase_connection.SupabaseConnection",
) -> entities.BackendUpdates:
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


def get_column_values(
    table_name: str,
    column_name: str,
    *,
    unique: bool = False,
    connection: "st_supabase_connection.SupabaseConnection",
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
