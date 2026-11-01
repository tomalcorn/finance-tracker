import type { QuickButtonMode, RawRow } from '@/domain/entities';
import type { QuickButtonView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';

/** The quick-button form's fields, as typed. */
export type ButtonDraft = {
  name: string;
  icon: string;
  mode: QuickButtonMode;
  paymentName: string;
  amount: string;
  bankAccountId: string | null;
  categoryId: string | null;
  position: string;
};

/** What is wrong with each field of a draft that has a problem. */
export type DraftErrors = Partial<Record<'name' | 'amount' | 'bankAccountId' | 'position', string>>;

/** The buttons in the order they are shown: by position, then by name. */
export function ordered(buttons: readonly QuickButtonView[]): QuickButtonView[] {
  return [...buttons].sort(
    (a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name),
  );
}

/** The position that puts a new button after every existing one. */
export function nextPosition(buttons: readonly QuickButtonView[]): number {
  return buttons.reduce((last, button) => Math.max(last, button.display_order + 1), 0);
}

/** A draft of an existing button, or of a new one at `position`. */
export function draftOf(button: QuickButtonView | null, position: number): ButtonDraft {
  return {
    name: button?.name ?? '',
    icon: button?.icon ?? '',
    mode: button?.mode ?? 'log',
    paymentName: button?.payment_name ?? '',
    amount: button?.expense == null ? '' : button.expense.toFixed(2),
    bankAccountId: button?.bank_account_id ?? null,
    categoryId: button?.category_id ?? null,
    position: String(button?.display_order ?? position),
  };
}

/**
 * Check a draft by the rules a quick button is saved under. Every button needs a name. A `log`
 * button also needs an amount and a bank account, because a tap gives it no chance to ask. An
 * amount may be negative (money coming back) but not zero.
 */
export function draftErrors(draft: ButtonDraft): DraftErrors {
  const errors: DraftErrors = {};
  const amount = parseAmount(draft.amount);
  if (!draft.name.trim()) errors.name = 'Give the button a name.';
  if (Number.isNaN(amount)) errors.amount = 'Enter an amount in pounds, e.g. 3.40.';
  else if (amount === 0) errors.amount = 'An amount can’t be zero. Leave it blank instead.';
  else if (amount === null && draft.mode === 'log') {
    errors.amount = 'A button that logs at once needs an amount.';
  }
  if (draft.bankAccountId === null && draft.mode === 'log') {
    errors.bankAccountId = 'A button that logs at once needs a bank account.';
  }
  if (!/^\d+$/.test(draft.position.trim())) errors.position = 'Enter a whole number, 0 or more.';
  return errors;
}

/** The raw row a valid draft saves as, over the button being edited when there is one. */
export function draftRow(draft: ButtonDraft, button: QuickButtonView | null): RawRow {
  return {
    ...button,
    name: draft.name.trim(),
    icon: draft.icon.trim() || null,
    mode: draft.mode,
    payment_name: draft.paymentName.trim() || null,
    expense: parseAmount(draft.amount),
    bank_account_id: draft.bankAccountId,
    category_id: draft.categoryId,
    display_order: Number(draft.position),
  };
}
