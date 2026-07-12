"""Client to support reading/writing/updating to supabase."""

from typing import TYPE_CHECKING, cast

from driven_adapters import errors

if TYPE_CHECKING:
    import st_supabase_connection

    from domain import entities


def _execute_query(
    query: "st_supabase_connection.SyncSelectRequestBuilder",
) -> "entities.JSON":
    """Execute the given query, translating any transport or API failure.

    Raises:
        errors.SupabaseAdapterError: the Supabase request did not complete.

    """
    try:
        response = query.execute()
    except Exception as e:
        msg = f"Supabase query failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e
    return response.data


def fetch_table(
    table_name: str,
    query_string: str,
    connection: "st_supabase_connection.SupabaseConnection",
) -> list["entities.JsonDict"]:
    """Fetch all rows from the specified table.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        connection: connection object to query against.

    Returns:
        A list of dictionaries representing the queried data.

    Raises:
        errors.AdapterError: If the backend does not return a list of rows.

    """
    query = connection.table(table_name).select(query_string)
    rows = _execute_query(query)
    if not isinstance(rows, list):
        msg = f"Expected a list of rows from {table_name}, got {type(rows).__name__}"
        raise errors.AdapterError(msg)
    return cast("list[entities.JsonDict]", rows)


def update_backend(
    table_name: str,
    updates: "entities.BackendUpdates",
    connection: "st_supabase_connection.SupabaseConnection",
) -> None:
    """Apply a batch of added, edited, and deleted rows to the backend.

    Args:
        table_name: The name of the table to update.
        updates: The BackendUpdates object containing added, edited, and deleted rows.
        connection: The Supabase connection to use.

    Raises:
        errors.SupabaseAdapterError: a Supabase write did not complete.

    """
    try:
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
    except Exception as e:
        msg = f"Supabase write to '{table_name}' failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e


def upsert_row(
    table_name: str,
    row: "entities.JsonDict",
    connection: "st_supabase_connection.SupabaseConnection",
) -> None:
    """Insert a single row, or update it in place when its primary key exists.

    Backs ``Repository.save``'s insert-or-update contract, so a fetched row that
    is mutated and saved does not collide with a plain insert's duplicate key.

    Args:
        table_name: The name of the table to write to.
        row: The full row payload to upsert.
        connection: The Supabase connection to use.

    Raises:
        errors.SupabaseAdapterError: the Supabase write did not complete.

    """
    try:
        connection.table(table_name).upsert(row).execute()
    except Exception as e:
        msg = f"Supabase write to '{table_name}' failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e
