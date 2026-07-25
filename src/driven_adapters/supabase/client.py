"""Client to support reading/writing/updating to supabase."""

from typing import TYPE_CHECKING, cast

from driven_adapters import errors

if TYPE_CHECKING:
    from collections.abc import Mapping

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
    eq_filters: "Mapping[str, str] | None" = None,
) -> list["entities.JsonDict"]:
    """Fetch rows from the specified table, optionally narrowed by equality.

    Args:
        table_name: The name of the table to query.
        query_string: The select query string.
        connection: connection object to query against.
        eq_filters: Optional ``column -> value`` equality filters, applied as
            chained ``.eq(column, value)`` clauses. Used for the ownership-scoped
            slice reads (e.g. ``ownership_type='joint'`` for a given
            ``joint_account_id``); omit for a whole-table read.

    Returns:
        A list of dictionaries representing the queried data.

    Raises:
        errors.AdapterError: If the backend does not return a list of rows.

    """
    query = connection.table(table_name).select(query_string)
    for column, value in (eq_filters or {}).items():
        query = query.eq(column, value)
    rows = _execute_query(query)
    if not isinstance(rows, list):
        msg = f"Expected a list of rows from {table_name}, got {type(rows).__name__}"
        raise errors.AdapterError(msg)
    return cast("list[entities.JsonDict]", rows)


def upsert_rows(
    table_name: str,
    rows: "list[entities.JsonDict]",
    connection: "st_supabase_connection.SupabaseConnection",
) -> None:
    """Insert full rows, updating in place any whose primary key already exists.

    Backs ``Repository.save_entities``: a fetched row that is copied with changes
    and saved must not collide with a plain insert's duplicate key.

    Args:
        table_name: The name of the table to write to.
        rows: The full row payloads to upsert.
        connection: The Supabase connection to use.

    Raises:
        errors.SupabaseAdapterError: the Supabase write did not complete.

    """
    try:
        connection.table(table_name).upsert(rows).execute()
    except Exception as e:
        msg = f"Supabase write to '{table_name}' failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e


def update_rows(
    table_name: str,
    edits: "entities.EditedRows",
    connection: "st_supabase_connection.SupabaseConnection",
) -> None:
    """Patch the given columns of existing rows, one request per row id.

    Args:
        table_name: The name of the table to update.
        edits: Changed columns keyed by row id.
        connection: The Supabase connection to use.

    Raises:
        errors.SupabaseAdapterError: a Supabase write did not complete.

    """
    try:
        for row_id, changes in edits.items():
            connection.table(table_name).update(changes).eq("id", row_id).execute()
    except Exception as e:
        msg = f"Supabase write to '{table_name}' failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e


def delete_rows(
    table_name: str,
    ids: "entities.DeletedIds",
    connection: "st_supabase_connection.SupabaseConnection",
) -> None:
    """Delete the rows with the given ids in one request.

    Args:
        table_name: The name of the table to delete from.
        ids: The ids of the rows to delete.
        connection: The Supabase connection to use.

    Raises:
        errors.SupabaseAdapterError: the Supabase write did not complete.

    """
    try:
        connection.table(table_name).delete().in_("id", ids).execute()
    except Exception as e:
        msg = f"Supabase write to '{table_name}' failed: {e}"
        raise errors.SupabaseAdapterError(msg) from e
