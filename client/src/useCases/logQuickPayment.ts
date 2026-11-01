import { today, type ExpensePayment, type Payment, type RawRow } from '@/domain/entities';
import type { PaymentView, QuickButtonView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { IncompleteQuickPaymentError, QuickPaymentWriteError } from '@/useCases/errors';

/** The payment fields a tap may fill in over a button's preset. */
export type PaymentOverrides = {
  name?: string;
  expense?: number | null;
  bank_account_id?: string | null;
  category_id?: string | null;
};

/**
 * The name a button presets for its payment. Only a `log` button falls back to its label: it has
 * no form to be told a name in. A `prompt` button that presets none is asking to be given one.
 */
export function presetName(button: QuickButtonView): string {
  if (button.payment_name) return button.payment_name;
  return button.mode === 'log' ? button.name : '';
}

/** The payment row a button fills in by itself: complete for `log`, with gaps for `prompt`. */
export function presetPayment(button: QuickButtonView): Required<PaymentOverrides> {
  return {
    name: presetName(button),
    expense: button.expense,
    bank_account_id: button.bank_account_id,
    category_id: button.category_id,
  };
}

/** What a payment still lacks, in words, for the fields a payment cannot be written without. */
export function missingFields(payment: PaymentOverrides): string[] {
  const missing: string[] = [];
  if (!payment.name) missing.push('a name');
  if (payment.expense === null || payment.expense === undefined) missing.push('an amount');
  if (!payment.bank_account_id) missing.push('a bank account');
  return missing;
}

/**
 * Log the expense a quick button stands for, dated today, through a payments repository in the
 * button's own ownership. A `prompt` button passes what its form collected as `overrides`.
 *
 * @returns The payment written, so the caller can confirm or undo it.
 * @throws {IncompleteQuickPaymentError} when a required field is neither preset nor supplied.
 * @throws {QuickPaymentWriteError} when the payment fails its rules or could not be written.
 */
export async function logQuickPayment(
  payments: Repository<Payment, PaymentView>,
  button: QuickButtonView,
  overrides: PaymentOverrides = {},
): Promise<ExpensePayment> {
  const payment = { ...presetPayment(button), ...overrides };
  const missing = missingFields(payment);
  if (missing.length > 0) throw new IncompleteQuickPaymentError(button.name, missing);

  const row: RawRow = { ...payment, payment_type: 'expense', payment_date: today() };
  try {
    const [built] = await payments.build([row]);
    if (built?.payment_type !== 'expense') {
      throw new QuickPaymentWriteError(`Quick button "${button.name}" built no expense.`);
    }
    await payments.save([built]);
    return built;
  } catch (error) {
    if (!(error instanceof RepositoryError)) throw error;
    throw new QuickPaymentWriteError(
      `Could not log a payment for quick button "${button.name}": ${error.message}`,
      { cause: error },
    );
  }
}
