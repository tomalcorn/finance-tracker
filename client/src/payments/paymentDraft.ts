import type { RawRow } from '@/domain/entities';
import type { PaymentView } from '@/domain/readModels';
import { parseAmount } from '@/theme/formatAmount';

/** Money out or money in. */
export type PaymentType = PaymentView['payment_type'];

/** The payment form's fields, as typed. */
export type PaymentDraft = {
  type: PaymentType;
  name: string;
  amount: string;
  /** `YYYY-MM-DD`. */
  date: string;
  bankAccountId: string | null;
  /** The category of an expense, or the income source of an income. */
  sourceId: string | null;
  checked: boolean;
};

/** What is wrong with each field of a draft that has a problem. */
export type PaymentDraftErrors = Partial<
  Record<'name' | 'amount' | 'date' | 'bankAccountId', string>
>;

/** A draft of an existing payment, or of a new expense on `date`. */
export function paymentDraftOf(payment: PaymentView | null, date: string): PaymentDraft {
  if (!payment) {
    return {
      type: 'expense',
      name: '',
      amount: '',
      date,
      bankAccountId: null,
      sourceId: null,
      checked: false,
    };
  }
  const income = payment.payment_type === 'income';
  return {
    type: payment.payment_type,
    name: payment.name,
    amount: (income ? payment.income : payment.expense).toFixed(2),
    date: payment.payment_date,
    bankAccountId: payment.bank_account_id,
    sourceId: income ? payment.income_source_id : payment.category_id,
    checked: payment.checked,
  };
}

/** Whether `text` is a real calendar date written `YYYY-MM-DD`. */
function isDate(text: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const [year = 0, month = 0, day = 0] = text.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.getMonth() === month - 1 && date.getDate() === day;
}

/**
 * Check a draft by the rules a payment is saved under: a name, a date, a bank account, and an
 * amount that may be negative (money coming back) but not zero.
 */
export function paymentDraftErrors(draft: PaymentDraft): PaymentDraftErrors {
  const errors: PaymentDraftErrors = {};
  const amount = parseAmount(draft.amount);
  if (!draft.name.trim()) errors.name = 'Give it a name.';
  if (amount === null) errors.amount = 'Enter the amount.';
  else if (Number.isNaN(amount)) errors.amount = 'Enter an amount in pounds, e.g. 3.40.';
  else if (amount === 0) errors.amount = 'An amount can’t be zero.';
  if (!isDate(draft.date)) errors.date = 'Enter a date, e.g. 2026-11-01.';
  if (draft.bankAccountId === null) errors.bankAccountId = 'Choose the account it moved through.';
  return errors;
}

/** The raw row a valid draft saves as, over the payment being edited when there is one. */
export function paymentRow(draft: PaymentDraft, payment: PaymentView | null): RawRow {
  const amount = parseAmount(draft.amount) ?? 0;
  const income = draft.type === 'income';
  return {
    ...payment,
    payment_type: draft.type,
    name: draft.name.trim(),
    payment_date: draft.date,
    expense: income ? 0 : amount,
    income: income ? amount : 0,
    bank_account_id: draft.bankAccountId,
    category_id: income ? null : draft.sourceId,
    income_source_id: income ? draft.sourceId : null,
    checked: draft.checked,
  };
}
