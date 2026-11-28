import type { RawRow } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { amountError, parseAmount, type AmountRule } from '@/theme/formatAmount';

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

/** A budget or a pot's target: zero or more, blank meaning zero. */
const PLANNED: AmountRule = { sign: 'nonnegative', optional: true };

/** Check a draft by the rules a category is saved under; a pot's fields only when it is one. */
export function categoryDraftErrors(draft: CategoryDraft, pot: boolean): CategoryDraftErrors {
  const errors: CategoryDraftErrors = {};
  if (!draft.name.trim()) errors.name = 'Give it a name.';
  const budget = amountError(draft.budget, PLANNED);
  if (budget) errors.budget = budget;
  if (pot) {
    const cost = amountError(draft.cost, PLANNED);
    if (cost) errors.cost = cost;
    const startingBalance = amountError(draft.startingBalance, { sign: 'any', optional: true });
    if (startingBalance) errors.startingBalance = startingBalance;
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
  return amountError(text, { sign: 'nonnegative' });
}

/** Check an amount as typed that may be negative, e.g. a pot's starting balance. */
export function signedAmountError(text: string): string | undefined {
  return amountError(text, { sign: 'any' });
}
