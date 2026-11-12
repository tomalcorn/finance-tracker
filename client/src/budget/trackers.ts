import type { SymbolViewProps } from 'expo-symbols';

import type { CategoryView, IncomeSourceView, PaymentView } from '@/domain/readModels';
import { formatAmount } from '@/theme/formatAmount';
import { sameMonth } from '@/theme/formatDate';

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

/**
 * The payments counted towards a subcategory, newest first: a pot's every payment, since it
 * fills up across months, or this month's for anything else.
 */
export function paymentsCountedIn(
  payments: readonly PaymentView[],
  category: CategoryView,
  today: string,
): PaymentView[] {
  const pot = category.accrual === 'multi_month';
  return payments
    .filter(
      (payment) =>
        payment.payment_type === 'expense' &&
        payment.category_id === category.id &&
        (pot || sameMonth(payment.payment_date, today)),
    )
    .sort((a, b) => b.payment_date.localeCompare(a.payment_date) || a.name.localeCompare(b.name));
}

/** Whether a budget is close enough to spent to warn: 90% used, or more. */
export function nearlySpent(category: CategoryView): boolean {
  return category.progress >= 90;
}

/** Rounds to whole pence, so sums of amounts don't leave a stray fraction of a penny. */
function pence(amount: number): number {
  return Math.round(amount * 100) / 100;
}

/** What banking this month's plan would do to a pot. */
export type PotPlan = {
  /** What is planned for the pot this month. */
  planned: number;
  /** What is left to save once the plan is banked. Negative when the plan is more than needed. */
  after: number;
  /** The plan as a percentage of the pot's cost, capped at what is still to go. */
  plannedProgress: number;
  /** The projection in words, e.g. "£36.00 to go after this month". */
  summary: string;
};

/**
 * What a pot's plan for the month would leave to go, or null when there is nothing to show:
 * nothing planned, or the pot already saved. `planned` stands in for the pot's own plan while
 * it is being edited.
 */
export function potPlan(pot: CategoryView, planned: number = pot.budget): PotPlan | null {
  if (!(planned > 0) || pot.remaining <= 0) return null;
  const after = pence(pot.remaining - planned);
  return {
    planned,
    after,
    plannedProgress: pot.cost > 0 ? (Math.min(planned, pot.remaining) / pot.cost) * 100 : 0,
    summary:
      after > 0
        ? `${formatAmount(after)} to go after this month`
        : after === 0
          ? 'Goal reached this month'
          : `Goal reached this month, ${formatAmount(-after)} more than needed`,
  };
}

/** Whether the pots' plans fit the tracker's budget, in words. */
export function plansFit(tracker: CategoryView, pots: readonly CategoryView[]) {
  const planned = pence(pots.reduce((total, pot) => total + pot.budget, 0));
  const left = pence(tracker.budget - planned);
  return {
    planned,
    left,
    summary:
      left < 0
        ? `${formatAmount(planned)} planned across pots · ${formatAmount(-left)} more than the budget`
        : left === 0
          ? `${formatAmount(planned)} planned across pots · all of the budget`
          : `${formatAmount(planned)} planned across pots · ${formatAmount(left)} of the budget unplanned`,
  };
}
