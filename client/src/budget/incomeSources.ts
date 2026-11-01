import type { IncomeRollUpPeriod, RawRow } from '@/domain/entities';
import type { CategoryView, IncomeSourceView, PaymentView } from '@/domain/readModels';
import { sameMonth } from '@/theme/formatDate';

/** The income source form's fields, as entered. */
export type IncomeSourceDraft = { name: string; trackerIds: string[] };

/** A date in the month whose income the budgets are split out of: this month, or the one before. */
export function rollUpDate(today: string, period: IncomeRollUpPeriod): string {
  if (period === 'current_month') return today;
  const [year = 0, month = 1] = today.split('-').map(Number);
  const previous = month === 1 ? `${year - 1}-12` : `${year}-${String(month - 1).padStart(2, '0')}`;
  return `${previous}-01`;
}

/** The income payments counted towards a source in its roll-up month, newest first. */
export function incomeCountedIn(
  payments: readonly PaymentView[],
  source: IncomeSourceView,
  today: string,
): PaymentView[] {
  const month = rollUpDate(today, source.income_roll_up_period);
  return payments
    .filter(
      (payment) =>
        payment.payment_type === 'income' &&
        payment.income_source_id === source.id &&
        sameMonth(payment.payment_date, month),
    )
    .sort((a, b) => b.payment_date.localeCompare(a.payment_date) || a.name.localeCompare(b.name));
}

/** Whether any payment, in any month, is booked to a source: the database won't delete one that is. */
export function hasPayments(payments: readonly PaymentView[], sourceId: string): boolean {
  return payments.some((payment) => payment.income_source_id === sourceId);
}

/** The names of the trackers a source funds, in the trackers' own order. */
export function fundedTrackers(
  source: IncomeSourceView,
  trackers: readonly CategoryView[],
): string[] {
  return trackers
    .filter((tracker) => source.budget_tracker_ids.includes(tracker.id))
    .map((tracker) => tracker.name);
}

/** A draft of an existing source, or a blank one. */
export function incomeSourceDraftOf(source: IncomeSourceView | null): IncomeSourceDraft {
  return { name: source?.name ?? '', trackerIds: [...(source?.budget_tracker_ids ?? [])] };
}

/** The raw row a draft saves as, over the source being edited when there is one. */
export function incomeSourceRow(draft: IncomeSourceDraft, source: IncomeSourceView | null): RawRow {
  return { ...source, name: draft.name.trim(), budget_tracker_ids: draft.trackerIds };
}
