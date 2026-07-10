"""Client to support reading/writing/updating to supabase."""

from typing import TYPE_CHECKING, cast

import pydantic

if TYPE_CHECKING:
    import st_supabase_connection

    from domain import entities

JsonDict = dict[str, pydantic.JsonValue]


def _execute_query(
    query: "st_supabase_connection.SyncSelectRequestBuilder",
) -> list[JsonDict]:
    """Execute the given query and return the data."""
    response = query.execute()
    return cast("list[JsonDict]", response.data or [])


def fetch_table(
    table_name: str,
    query_string: str,
    connection: "st_supabase_connection.SupabaseConnection",
) -> list[JsonDict]:
    """Fetch all rows from the specified table.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        connection: connection object to query against.

    Returns:
        A list of dictionaries representing the queried data.

    """
    query = connection.table(table_name).select(query_string)
    return _execute_query(query)


def update_backend(
    table_name: str,
    updates: "entities.BackendUpdates",
    connection: "st_supabase_connection.SupabaseConnection",
) -> "entities.BackendUpdates":
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
