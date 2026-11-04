import type { SelectOption } from '@/components/SelectField';
import type { Contribution } from '@/ports/repositories';
import { parseAmount } from '@/theme/formatAmount';
import { isCalendarDate } from '@/theme/formatDate';

/** The contribution form's fields, as typed. */
export type ContributionDraft = {
  amount: string;
  /** `YYYY-MM-DD`. */
  date: string;
  fromBankAccountId: string | null;
  toBankAccountId: string | null;
  incomeSourceId: string | null;
};

/** What is wrong with each field of a draft that has a problem. */
export type ContributionDraftErrors = Partial<Record<keyof ContributionDraft, string>>;

function onlyChoice(options: readonly SelectOption[]): string | null {
  return options.length === 1 ? (options[0]?.value ?? null) : null;
}

/** A draft for `date`, with any choice that has only one option already made. */
export function contributionDraftOf(
  date: string,
  personalAccounts: readonly SelectOption[],
  jointAccounts: readonly SelectOption[],
  incomeSources: readonly SelectOption[],
): ContributionDraft {
  return {
    amount: '',
    date,
    fromBankAccountId: onlyChoice(personalAccounts),
    toBankAccountId: onlyChoice(jointAccounts),
    incomeSourceId: onlyChoice(incomeSources),
  };
}

/** Check a draft: an amount above zero, a date, and all three choices made. */
export function contributionDraftErrors(draft: ContributionDraft): ContributionDraftErrors {
  const errors: ContributionDraftErrors = {};
  const amount = parseAmount(draft.amount);
  if (amount === null) errors.amount = 'Enter the amount.';
  else if (Number.isNaN(amount)) errors.amount = 'Enter an amount in pounds, e.g. 150.';
  else if (amount <= 0) errors.amount = 'A contribution must be more than zero.';
  if (!isCalendarDate(draft.date)) errors.date = 'Enter a date, e.g. 2026-11-01.';
  if (draft.fromBankAccountId === null) {
    errors.fromBankAccountId = 'Choose the account it leaves.';
  }
  if (draft.toBankAccountId === null) {
    errors.toBankAccountId = 'Choose the joint account it arrives in.';
  }
  if (draft.incomeSourceId === null) {
    errors.incomeSourceId = 'Choose the income source to book it against.';
  }
  return errors;
}

/** The contribution a valid draft makes, or null while it has a problem. */
export function contributionOf(draft: ContributionDraft): Contribution | null {
  const amount = parseAmount(draft.amount);
  const { fromBankAccountId, toBankAccountId, incomeSourceId } = draft;
  if (
    Object.keys(contributionDraftErrors(draft)).length > 0 ||
    amount === null ||
    fromBankAccountId === null ||
    toBankAccountId === null ||
    incomeSourceId === null
  ) {
    return null;
  }
  return {
    amount,
    fromBankAccountId,
    toBankAccountId,
    incomeSourceId,
    paymentDate: draft.date,
  };
}
