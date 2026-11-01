import { PaymentSchema, today, type Payment, type RawRow } from '@/domain/entities';
import type { PaymentView, QuickButtonView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { IncompleteQuickPaymentError, QuickPaymentWriteError } from '@/useCases/errors';
import { logQuickPayment } from '@/useCases/logQuickPayment';

const USER_ID = 'auth0|65f0c2a1b3d4e5f6a7b8c9d0';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';
const OTHER_BANK_ACCOUNT_ID = '7e1a4c2b-9d3f-4a6e-8b5c-2f1d7a9e3b04';

const LOG_BUTTON: QuickButtonView = {
  id: '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01',
  user_id: USER_ID,
  name: 'Coffee',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  mode: 'log',
  payment_name: null,
  expense: 3.4,
  bank_account_id: BANK_ACCOUNT_ID,
  category_id: null,
  icon: '☕',
  display_order: 0,
};

const PROMPT_BUTTON: QuickButtonView = {
  ...LOG_BUTTON,
  name: 'Groceries',
  mode: 'prompt',
  expense: null,
};

/** A payments repository that builds through the real schema and keeps what it is asked to save. */
class StubPayments implements Repository<Payment, PaymentView> {
  readonly cacheKey = ['payments'];
  readonly saved: Payment[] = [];
  failWith: Error | null = null;

  async rows() {
    return [];
  }

  async build(rows: readonly RawRow[]) {
    return rows.map((row) => PaymentSchema.parse({ ...row, user_id: USER_ID }));
  }

  async save(items: readonly Payment[]) {
    if (this.failWith) throw this.failWith;
    this.saved.push(...items);
  }

  async delete() {}
}

let payments: StubPayments;

beforeEach(() => {
  payments = new StubPayments();
});

describe('logQuickPayment', () => {
  it('writes a log button’s preset as an expense', async () => {
    await logQuickPayment(payments, LOG_BUTTON);

    expect(payments.saved).toEqual([
      expect.objectContaining({
        payment_type: 'expense',
        expense: 3.4,
        bank_account_id: BANK_ACCOUNT_ID,
      }),
    ]);
  });

  it('dates the payment today', async () => {
    const payment = await logQuickPayment(payments, LOG_BUTTON);

    expect(payment.payment_date).toBe(today());
  });

  it('names a log button’s payment after the button when it presets no name', async () => {
    const payment = await logQuickPayment(payments, LOG_BUTTON);

    expect(payment.name).toBe('Coffee');
  });

  it('prefers the preset payment name over the button’s', async () => {
    const payment = await logQuickPayment(payments, { ...LOG_BUTTON, payment_name: 'Pret' });

    expect(payment.name).toBe('Pret');
  });

  it('logs a negative amount, for money coming back', async () => {
    const payment = await logQuickPayment(payments, { ...LOG_BUTTON, expense: -2.5 });

    expect(payment.expense).toBe(-2.5);
  });

  it('lays what the form filled in over the preset', async () => {
    const payment = await logQuickPayment(payments, PROMPT_BUTTON, {
      name: 'Tesco',
      expense: 46.2,
      bank_account_id: OTHER_BANK_ACCOUNT_ID,
    });

    expect(payment).toMatchObject({
      name: 'Tesco',
      expense: 46.2,
      bank_account_id: OTHER_BANK_ACCOUNT_ID,
    });
  });

  it('refuses a prompt button tapped without the details it asks for', async () => {
    await expect(logQuickPayment(payments, PROMPT_BUTTON)).rejects.toMatchObject({
      constructor: IncompleteQuickPaymentError,
      buttonName: 'Groceries',
      missing: ['a name', 'an amount'],
    });
  });

  it('does not borrow a prompt button’s label as the payment name', async () => {
    await expect(logQuickPayment(payments, PROMPT_BUTTON, { expense: 12 })).rejects.toMatchObject({
      missing: ['a name'],
    });
  });

  it('writes nothing when the payment is incomplete', async () => {
    await logQuickPayment(payments, PROMPT_BUTTON).catch(() => {});

    expect(payments.saved).toEqual([]);
  });

  it('reports a failed write as a quick-payment error, keeping the cause', async () => {
    const cause = new RepositoryError('network down');
    payments.failWith = cause;

    await expect(logQuickPayment(payments, LOG_BUTTON)).rejects.toMatchObject({
      constructor: QuickPaymentWriteError,
      cause,
    });
  });
});
