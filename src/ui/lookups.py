"""Shared id -> name lookups for reference data.

Used to populate selectbox options and render labels.
"""


from typing import TYPE_CHECKING

from ui import data_client

if TYPE_CHECKING:
    from collections.abc import Callable


def get_id_name_map(table_name: str) -> dict[str, str]:
    """Return a {id: name} map for every row in `table_name`."""
    rows = data_client.get_data(table_name=table_name, query_string="*")
    return {str(row["id"]): str(row["name"]) for row in rows}


def make_name_formatter(
    id_name_map: dict[str, str],
    fallback: str = "Unknown",
) -> "Callable[[str | float | None], str]":
    """Build a format_func that looks up a name, falling back gracefully."""

    def _format(item_id: str | float | None) -> str:
        return id_name_map.get(str(item_id), fallback)

    return _format
