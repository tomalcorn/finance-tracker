import { PaymentSchema, type Payment, type RawRow } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { MoveSavingsError } from '@/useCases/errors';
import { moveSavings, type SavingsMove } from '@/useCases/moveSavings';

const USER_ID = 'auth0|65f0c2a1b3d4e5f6a7b8c9d0';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';

const SAVINGS: CategoryView = {
  id: '1a2b3c4d-0000-4000-8000-000000000003',
  user_id: USER_ID,
  name: 'Savings',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  parent_id: null,
  budget: 500,
  accrual: 'monthly',
  cost: 0,
  starting_balance: 0,
  accrued: 0,
  remaining: 500,
  progress: 0,
  split: 0,
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

const DEPOSIT: SavingsMove = {
  direction: 'deposit',
  amount: 50,
  bankAccountId: BANK_ACCOUNT_ID,
  paymentDate: '2026-11-01',
  name: 'Savings deposit',
};

let payments: StubPayments;

beforeEach(() => {
  payments = new StubPayments();
});

describe('moveSavings', () => {
  it('books a deposit as an expense to savings, from the chosen account', async () => {
    await moveSavings(payments, SAVINGS, DEPOSIT);

    expect(payments.saved).toEqual([
      expect.objectContaining({
        payment_type: 'expense',
        name: 'Savings deposit',
        expense: 50,
        category_id: SAVINGS.id,
        bank_account_id: BANK_ACCOUNT_ID,
      }),
    ]);
  });

  it('books a withdrawal as a negative expense to savings', async () => {
    await moveSavings(payments, SAVINGS, { ...DEPOSIT, direction: 'withdraw', amount: 30 });

    expect(payments.saved).toEqual([
      expect.objectContaining({ expense: -30, category_id: SAVINGS.id }),
    ]);
  });

  it('dates the payment as asked', async () => {
    const written = await moveSavings(payments, SAVINGS, { ...DEPOSIT, paymentDate: '2026-10-15' });

    expect(written.payment_date).toBe('2026-10-15');
  });

  it('names the payment as asked', async () => {
    const written = await moveSavings(payments, SAVINGS, { ...DEPOSIT, name: 'Bonus' });

    expect(written.name).toBe('Bonus');
  });

  it('reports a failed write as a savings error, keeping the cause', async () => {
    const cause = new RepositoryError('network down');
    payments.failWith = cause;

    await expect(moveSavings(payments, SAVINGS, DEPOSIT)).rejects.toMatchObject({
      constructor: MoveSavingsError,
      cause,
    });
  });
});
