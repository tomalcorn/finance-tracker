import type { Cadence, RawRow } from '@/domain/entities';
import type { SubscriptionView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';
import { isCalendarDate } from '@/theme/formatDate';

/** The cadences to choose from, with how each reads. */
export const CADENCES: readonly { value: Cadence; label: string }[] = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'biannually', label: 'Twice a year' },
  { value: 'yearly', label: 'Yearly' },
];

/** The subscription form's fields, as typed. */
export type SubscriptionDraft = {
  name: string;
  amount: string;
  cadence: Cadence;
  bankAccountId: string | null;
  categoryId: string | null;
  /** `YYYY-MM-DD`. */
  startDate: string;
  /** `YYYY-MM-DD`, or blank when it is ongoing. */
  endDate: string;
  isActive: boolean;
  jointBankAccountId: string | null;
  jointIncomeSourceId: string | null;
};

/** What is wrong with each field of a draft that has a problem. */
export type SubscriptionDraftErrors = Partial<
  Record<
    | 'name'
    | 'amount'
    | 'bankAccountId'
    | 'startDate'
    | 'endDate'
    | 'jointBankAccountId'
    | 'jointIncomeSourceId',
    string
  >
>;

/** A draft of an existing subscription, or of a new monthly one starting on `today`. */
export function subscriptionDraftOf(
  subscription: SubscriptionView | null,
  today: string,
): SubscriptionDraft {
  return {
    name: subscription?.name ?? '',
    amount: subscription ? subscription.amount.toFixed(2) : '',
    cadence: subscription?.cadence ?? 'monthly',
    bankAccountId: subscription?.bank_account_id ?? null,
    categoryId: subscription?.category_id ?? null,
    startDate: subscription?.start_date ?? today,
    endDate: subscription?.end_date ?? '',
    isActive: subscription?.is_active ?? true,
    jointBankAccountId: subscription?.joint_bank_account_id ?? null,
    jointIncomeSourceId: subscription?.joint_income_source_id ?? null,
  };
}

/**
 * Check a draft by the rules a subscription is saved under: a name, an amount, a bank account, and
 * a start date, with any end date not before it. A joint contribution also needs the joint account
 * the money arrives in and the income source it is booked against.
 */
export function subscriptionDraftErrors(
  draft: SubscriptionDraft,
  contribution: boolean,
): SubscriptionDraftErrors {
  const errors: SubscriptionDraftErrors = {};
  const amount = parseAmount(draft.amount);
  const endDate = draft.endDate.trim();
  if (!draft.name.trim()) errors.name = 'Give it a name.';
  if (amount === null) errors.amount = 'Enter the amount.';
  else if (Number.isNaN(amount)) errors.amount = 'Enter an amount in pounds, e.g. 9.99.';
  else if (amount === 0) errors.amount = 'An amount can’t be zero.';
  if (draft.bankAccountId === null) errors.bankAccountId = 'Choose the account it leaves from.';
  if (!isCalendarDate(draft.startDate)) errors.startDate = 'Enter a date, e.g. 2026-11-01.';
  if (endDate !== '' && !isCalendarDate(endDate)) {
    errors.endDate = 'Enter a date, e.g. 2026-11-01, or leave it empty.';
  } else if (endDate !== '' && endDate < draft.startDate) {
    errors.endDate = 'It can’t end before it starts.';
  }
  if (contribution && draft.jointBankAccountId === null) {
    errors.jointBankAccountId = 'Choose the joint account it arrives in.';
  }
  if (contribution && draft.jointIncomeSourceId === null) {
    errors.jointIncomeSourceId = 'Choose the income source it goes against.';
  }
  return errors;
}

/**
 * The raw row a valid draft saves as, over the subscription being edited when there is one.
 *
 * Args:
 *   contribution: Save it as a joint contribution, booked against `jointCategoryId` rather than a
 *     chosen category. Left false, the joint columns stay as they are, so a contribution shown in
 *     the ordinary list for want of a joint account is not turned into an ordinary subscription.
 *   jointCategoryId: The personal "Joint" budget tracker.
 */
export function subscriptionRow(
  draft: SubscriptionDraft,
  subscription: SubscriptionView | null,
  contribution: boolean,
  jointCategoryId: string | null,
): RawRow {
  return {
    ...subscription,
    name: draft.name.trim(),
    amount: parseAmount(draft.amount) ?? 0,
    cadence: draft.cadence,
    bank_account_id: draft.bankAccountId,
    start_date: draft.startDate,
    end_date: draft.endDate.trim() || null,
    is_active: draft.isActive,
    category_id: contribution ? (subscription?.category_id ?? jointCategoryId) : draft.categoryId,
    ...(contribution
      ? {
          joint_bank_account_id: draft.jointBankAccountId,
          joint_income_source_id: draft.jointIncomeSourceId,
        }
      : {}),
  };
}
