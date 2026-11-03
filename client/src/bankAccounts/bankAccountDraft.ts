import type { RawRow } from '@/domain/entities';
import type { BankAccountView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';

/** The bank account form's fields, as typed. */
export type BankAccountDraft = { name: string; startingBalance: string };

/** What is wrong with each field of a draft that has a problem. */
export type BankAccountDraftErrors = Partial<Record<keyof BankAccountDraft, string>>;

/** A draft of an existing account, or a blank one. */
export function bankAccountDraftOf(account: BankAccountView | null): BankAccountDraft {
  return {
    name: account?.name ?? '',
    startingBalance: account ? account.starting_balance.toFixed(2) : '',
  };
}

/** Check a draft: an account needs a name and a starting balance, which may be below zero. */
export function bankAccountDraftErrors(draft: BankAccountDraft): BankAccountDraftErrors {
  const errors: BankAccountDraftErrors = {};
  const balance = parseAmount(draft.startingBalance);
  if (!draft.name.trim()) errors.name = 'Give it a name.';
  if (balance === null) errors.startingBalance = 'Enter the starting balance, or 0.';
  else if (Number.isNaN(balance)) {
    errors.startingBalance = 'Enter an amount in pounds, e.g. 1200.50.';
  }
  return errors;
}

/** The raw row a valid draft saves as, over the account being edited when there is one. */
export function bankAccountRow(draft: BankAccountDraft, account: BankAccountView | null): RawRow {
  return {
    ...account,
    name: draft.name.trim(),
    starting_balance: parseAmount(draft.startingBalance) ?? 0,
  };
}
