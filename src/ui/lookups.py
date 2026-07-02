"""Helpers for rendering id -> name reference data in the UI.

The id -> name maps themselves are per-aggregate reads built in
``composition.wiring`` (e.g. ``wiring.bank_account_id_name_map``); this module
only turns such a map into a Streamlit ``format_func``.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def make_name_formatter(
    id_name_map: dict[str, str],
    fallback: str = "Unknown",
) -> "Callable[[str | float | None], str]":
    """Build a format_func that looks up a name, falling back gracefully."""

    def _format(item_id: str | float | None) -> str:
        return id_name_map.get(str(item_id), fallback)

    return _format
