"""Helpers for rendering id -> name reference data in the UI.

The id -> name maps themselves are per-aggregate reads built in
``composition.wiring`` (e.g. ``wiring.bank_account_id_name_map``); this module
turns such a map into a Streamlit ``format_func``, and builds the one map whose
labels are a display decision rather than a column: the category tree's.
"""

import collections
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from domain import entities

CATEGORY_SEPARATOR = " - "
"""What sits between a parent's name and its child's in a picker label."""


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

    A payment may be attributed to a root or to one of its children, so the
    picker offers every category. Two things make a flat list of them readable,
    and both are display decisions built here from ``parent_id`` rather than
    stored as a denormalised path:

    * a child is labelled ``"Parent - Child"``, and
    * each root is immediately followed by its own children, since scanning a
      long list grouped by parent is far easier than roots-then-everything.

    ``st.column_config.SelectboxColumn`` has no option grouping, so the prefix
    does the work a group header would. Insertion order is the order a caller
    gets from ``list(map)``, which is what the options list is built from.

    Args:
        categories: Every category of one ownership half, in any order.

    Returns:
        ``{id: label}``, ordered root-then-its-children, each level sorted by
        name. A child whose parent is absent keeps its bare name and follows the
        grouped entries, so it can still be picked.

    """
    children_by_parent: dict[str, list[entities.CategoryModel]] = (
        collections.defaultdict(list)
    )
    for category in categories:
        if not category.is_root:
            children_by_parent[str(category.parent_id)].append(category)

    def by_name(category: "entities.CategoryModel") -> str:
        return str(category.name)

    labels: dict[str, str] = {}
    for root in sorted((c for c in categories if c.is_root), key=by_name):
        labels[str(root.id)] = str(root.name)
        for child in sorted(children_by_parent.pop(str(root.id), []), key=by_name):
            labels[str(child.id)] = f"{root.name}{CATEGORY_SEPARATOR}{child.name}"

    for orphans in children_by_parent.values():
        for child in sorted(orphans, key=by_name):
            labels[str(child.id)] = str(child.name)
    return labels
