import type { SymbolViewProps } from 'expo-symbols';

import type { CategoryView, IncomeSourceView } from '@/domain/readModels';

/** The budget trackers every workspace is seeded with, in the order they are shown. */
export const TRACKER_ORDER = ['Expenses', 'Joint', 'One-offs', 'Savings'] as const;

const TRACKER_ICONS: Record<string, SymbolViewProps['name']> = {
  Expenses: { ios: 'minus.circle.fill', web: 'do_not_disturb_on' },
  Joint: { ios: 'person.2.fill', web: 'group' },
  'One-offs': { ios: 'circle.hexagongrid.fill', web: 'bubble_chart' },
  Savings: { ios: 'banknote.fill', web: 'savings' },
};

const DEFAULT_ICON: SymbolViewProps['name'] = { ios: 'chart.pie.fill', web: 'pie_chart' };

/** A tracker's icon, by its name. */
export function trackerIcon(name: string): SymbolViewProps['name'] {
  return TRACKER_ICONS[name] ?? DEFAULT_ICON;
}

/** The budget trackers (the categories with no parent), in `TRACKER_ORDER`, then by name. */
export function roots(categories: readonly CategoryView[]): CategoryView[] {
  const rank = (name: string) => {
    const index = (TRACKER_ORDER as readonly string[]).indexOf(name);
    return index === -1 ? TRACKER_ORDER.length : index;
  };
  return categories
    .filter((category) => category.parent_id === null)
    .sort((a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name));
}

/** The subcategories under one tracker, by name. */
export function childrenOf(categories: readonly CategoryView[], rootId: string): CategoryView[] {
  return categories
    .filter((category) => category.parent_id === rootId)
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Whether a tracker's subcategories are pots, filled up across months, rather than monthly. */
export function holdsPots(root: CategoryView): boolean {
  return root.name === 'One-offs';
}

/** Whether a tracker is meant to be broken down into subcategories. Joint and Savings are one pot each. */
export function takesSubcategories(root: CategoryView): boolean {
  return root.name !== 'Joint' && root.name !== 'Savings';
}

/** What the tracker budgets are split out of: the income sources' totals for the roll-up month. */
export function totalIncome(incomeSources: readonly IncomeSourceView[]): number {
  return incomeSources.reduce((total, source) => total + source.current_month, 0);
}

/** The sum of the trackers' monthly budgets. */
export function totalAllocated(trackers: readonly CategoryView[]): number {
  return trackers.reduce((total, tracker) => total + tracker.budget, 0);
}

/** Whether a budget is close enough to spent to warn: 90% used, or more. */
export function nearlySpent(category: CategoryView): boolean {
  return category.progress >= 90;
}
