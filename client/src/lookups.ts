import type { SelectOption } from '@/components/SelectField';
import type { CategoryView } from '@/domain/readModels';

/** One choice per row, by name, in name order. */
export function nameOptions(rows: readonly { id: string; name: string }[]): SelectOption[] {
  return [...rows]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((row) => ({ value: row.id, label: row.name }));
}

/**
 * A choice per category, both levels of the tree: each budget tracker followed by its
 * subcategories, labelled "Tracker - Subcategory", every level in name order. A subcategory whose
 * tracker is missing keeps its own name and comes last.
 */
export function categoryOptions(categories: readonly CategoryView[]): SelectOption[] {
  const byName = (a: CategoryView, b: CategoryView) => a.name.localeCompare(b.name);
  const roots = categories.filter((category) => category.parent_id === null).sort(byName);
  const children = categories.filter((category) => category.parent_id !== null).sort(byName);
  const placed = new Set<string>();

  const options = roots.flatMap((root) => [
    { value: root.id, label: root.name },
    ...children
      .filter((child) => child.parent_id === root.id)
      .map((child) => {
        placed.add(child.id);
        return { value: child.id, label: `${root.name} - ${child.name}` };
      }),
  ]);
  const orphans = children
    .filter((child) => !placed.has(child.id))
    .map((child) => ({ value: child.id, label: child.name }));
  return [...options, ...orphans];
}
