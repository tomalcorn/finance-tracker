import type { RawRow } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';

/** The subcategory form's fields, as typed. A monthly subcategory uses only `name` and `budget`. */
export type CategoryDraft = {
  name: string;
  /** The monthly budget, or for a pot what is planned to go into it this month. */
  budget: string;
  /** A pot's target. */
  cost: string;
  /** What a pot already held when it was started. */
  startingBalance: string;
};

export type CategoryDraftErrors = Partial<Record<keyof CategoryDraft, string>>;

function amountText(value: number | undefined): string {
  return value ? value.toFixed(2) : '';
}

/** A draft of an existing subcategory, or a blank one. */
export function categoryDraftOf(category: CategoryView | null): CategoryDraft {
  return {
    name: category?.name ?? '',
    budget: amountText(category?.budget),
    cost: amountText(category?.cost),
    startingBalance: amountText(category?.starting_balance),
  };
}

/** Check a non-negative amount where blank means zero. */
function nonNegative(text: string): string | undefined {
  const amount = parseAmount(text);
  if (Number.isNaN(amount)) return 'Enter an amount in pounds, e.g. 120.';
  if (amount !== null && amount < 0) return 'Enter an amount of 0 or more.';
  return undefined;
}

/** Check a draft by the rules a category is saved under; a pot's fields only when it is one. */
export function categoryDraftErrors(draft: CategoryDraft, pot: boolean): CategoryDraftErrors {
  const errors: CategoryDraftErrors = {};
  if (!draft.name.trim()) errors.name = 'Give it a name.';
  const budget = nonNegative(draft.budget);
  if (budget) errors.budget = budget;
  if (pot) {
    const cost = nonNegative(draft.cost);
    if (cost) errors.cost = cost;
    if (Number.isNaN(parseAmount(draft.startingBalance))) {
      errors.startingBalance = 'Enter an amount in pounds, e.g. 50.';
    }
  }
  return errors;
}

/**
 * The raw row a valid draft saves as: a subcategory of `root`, over the one being edited when
 * there is one. A pot accrues across months; anything else resets each month.
 */
export function categoryDraftRow(
  draft: CategoryDraft,
  root: CategoryView,
  pot: boolean,
  category: CategoryView | null,
): RawRow {
  return {
    ...category,
    name: draft.name.trim(),
    parent_id: root.id,
    accrual: pot ? 'multi_month' : 'monthly',
    budget: parseAmount(draft.budget) ?? 0,
    cost: pot ? (parseAmount(draft.cost) ?? 0) : (category?.cost ?? 0),
    starting_balance: pot
      ? (parseAmount(draft.startingBalance) ?? 0)
      : (category?.starting_balance ?? 0),
  };
}

/** Check a tracker's monthly budget as typed. */
export function trackerBudgetError(text: string): string | undefined {
  if (parseAmount(text) === null) return 'Enter a budget, or 0.';
  return nonNegative(text);
}

/** Check an amount as typed that may be negative, e.g. a pot's starting balance. */
export function signedAmountError(text: string): string | undefined {
  const amount = parseAmount(text);
  if (amount === null) return 'Enter an amount, or 0.';
  if (Number.isNaN(amount)) return 'Enter an amount in pounds, e.g. 50.';
  return undefined;
}
