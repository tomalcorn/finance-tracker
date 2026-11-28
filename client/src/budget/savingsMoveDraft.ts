import type { SelectOption } from '@/components/SelectField';
import { parseAmount } from '@/theme/formatAmount';
import { isCalendarDate } from '@/theme/formatDate';
import type { SavingsDirection, SavingsMove } from '@/useCases/moveSavings';

/** The savings move form's fields, as typed. */
export type SavingsMoveDraft = {
  amount: string;
  bankAccountId: string | null;
  /** `YYYY-MM-DD`. */
  date: string;
  name: string;
};

/** What is wrong with each field of a draft that has a problem. */
export type SavingsMoveDraftErrors = Partial<Record<keyof SavingsMoveDraft, string>>;

/** The name a move is booked under when none is typed. */
export const SAVINGS_MOVE_NAMES: Record<SavingsDirection, string> = {
  deposit: 'Savings deposit',
  withdraw: 'Savings withdrawal',
};

/** A draft for `date`, with the first account already chosen. */
export function savingsMoveDraftOf(
  date: string,
  bankAccounts: readonly SelectOption[],
): SavingsMoveDraft {
  return { amount: '', bankAccountId: bankAccounts[0]?.value ?? null, date, name: '' };
}

/**
 * Check a draft as it is typed: an amount above zero, an account and a date. A blank amount is not
 * flagged, since the form starts blank; `savingsMoveOf` still waits for one.
 */
export function savingsMoveDraftErrors(draft: SavingsMoveDraft): SavingsMoveDraftErrors {
  const errors: SavingsMoveDraftErrors = {};
  const amount = parseAmount(draft.amount);
  if (Number.isNaN(amount)) errors.amount = 'Enter an amount in pounds, e.g. 50.00.';
  else if (amount !== null && amount <= 0) errors.amount = 'Enter an amount above zero.';
  if (draft.bankAccountId === null) errors.bankAccountId = 'Choose an account.';
  if (!isCalendarDate(draft.date)) errors.date = 'Enter a date, e.g. 2026-11-01.';
  return errors;
}

/** The move a valid draft makes, under the default name when none is typed; null until then. */
export function savingsMoveOf(
  draft: SavingsMoveDraft,
  direction: SavingsDirection,
): SavingsMove | null {
  const amount = parseAmount(draft.amount);
  const { bankAccountId } = draft;
  if (
    Object.keys(savingsMoveDraftErrors(draft)).length > 0 ||
    amount === null ||
    bankAccountId === null
  ) {
    return null;
  }
  return {
    direction,
    amount,
    bankAccountId,
    paymentDate: draft.date,
    name: draft.name.trim() || SAVINGS_MOVE_NAMES[direction],
  };
}
