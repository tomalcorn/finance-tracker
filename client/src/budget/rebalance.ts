import { trackerBudgetError } from '@/budget/categoryDraft';
import type { RawRow } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';

/** Budgets typed in but not saved, as text, by tracker id. */
export type BudgetEdits = Readonly<Record<string, string>>;

/** A tracker's budget as it stands with the edits: the typed one if it reads, else the saved one. */
export function draftBudget(tracker: CategoryView, edits: BudgetEdits): number {
  const typed = edits[tracker.id];
  if (typed === undefined || trackerBudgetError(typed)) return tracker.budget;
  return parseAmount(typed) ?? tracker.budget;
}

/** What is wrong with each edited budget that has a problem, by tracker id. */
export function editErrors(edits: BudgetEdits): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [id, text] of Object.entries(edits)) {
    const error = trackerBudgetError(text);
    if (error) errors[id] = error;
  }
  return errors;
}

/** The rows to save: each tracker whose edited budget differs from the saved one. */
export function changedRows(trackers: readonly CategoryView[], edits: BudgetEdits): RawRow[] {
  return trackers
    .filter((tracker) => draftBudget(tracker, edits) !== tracker.budget)
    .map((tracker) => ({ ...tracker, budget: draftBudget(tracker, edits) }));
}
