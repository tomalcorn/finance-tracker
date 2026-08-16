"""Helpers for rendering id -> name reference data in the UI.

The id -> name maps themselves are per-aggregate reads built in
``composition.wiring`` (e.g. ``wiring.bank_account_id_name_map``); this module
turns such a map into a Streamlit ``format_func``, and builds the category
tree's own labels.
"""

import collections
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from domain import entities


def make_name_formatter(
    id_name_map: dict[str, str],
    fallback: str = "Unknown",
) -> "Callable[[str | float | None], str]":
    """Build a format_func that looks up a name, falling back gracefully."""

    def _format(item_id: str | float | None) -> str:
        return id_name_map.get(str(item_id), fallback)

    return _format


def make_category_name_map(
    categories: "Sequence[entities.CategoryModel]",
) -> dict[str, str]:
    """Return an ordered ``{id: label}`` map covering both levels of the tree.

    Args:
        categories: Every category of one ownership half, in any order.

    Returns:
        ``{id: label}``, every root first and then the children, each grouped
        under its own parent and every level sorted by name. A child is
        labelled ``"Parent - Child"``; one whose parent is absent keeps its bare
        name and comes last.

    """
    children_by_parent: dict[str, list[entities.CategoryModel]] = (
        collections.defaultdict(list)
    )
    for category in categories:
        if not category.is_root:
            children_by_parent[str(category.parent_id)].append(category)

    def by_name(category: "entities.CategoryModel") -> str:
        return str(category.name)

    roots = sorted((c for c in categories if c.is_root), key=by_name)
    labels = {str(root.id): str(root.name) for root in roots}

    for root in roots:
        for child in sorted(children_by_parent.pop(str(root.id), []), key=by_name):
            labels[str(child.id)] = f"{root.name} - {child.name}"

    for orphans in children_by_parent.values():
        for child in sorted(orphans, key=by_name):
            labels[str(child.id)] = str(child.name)
    return labels
