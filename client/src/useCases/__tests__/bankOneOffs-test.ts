import { PaymentSchema, type Payment, type RawRow } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { bankOneOffs } from '@/useCases/bankOneOffs';
import { BankOneOffsError, NothingToBankError } from '@/useCases/errors';

const USER_ID = 'auth0|65f0c2a1b3d4e5f6a7b8c9d0';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';

function pot(id: string, name: string, budget: number): CategoryView {
  return {
    id,
    user_id: USER_ID,
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: '1a2b3c4d-0000-4000-8000-000000000009',
    budget,
    accrual: 'multi_month',
    cost: 600,
    starting_balance: 0,
    accrued: 0,
    remaining: 600,
    progress: 0,
    split: 0,
  };
}

const BIKE = pot('1a2b3c4d-0000-4000-8000-000000000001', 'Bike', 50);
const SOFA = pot('1a2b3c4d-0000-4000-8000-000000000002', 'Sofa', 120);

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

describe('bankOneOffs', () => {
  it('pays each pot’s plan into it, from the chosen account', async () => {
    await bankOneOffs(payments, [BIKE, SOFA], BANK_ACCOUNT_ID, '2026-11-01');

    expect(payments.saved).toEqual([
      expect.objectContaining({ name: 'Bank: Bike', expense: 50, category_id: BIKE.id }),
      expect.objectContaining({ name: 'Bank: Sofa', expense: 120, category_id: SOFA.id }),
    ]);
  });

  it('dates the payments as asked', async () => {
    const [written] = await bankOneOffs(payments, [BIKE], BANK_ACCOUNT_ID, '2026-11-01');

    expect(written?.payment_date).toBe('2026-11-01');
  });

  it('refuses a pot with nothing planned, naming it', async () => {
    await expect(
      bankOneOffs(payments, [BIKE, pot(SOFA.id, 'Sofa', 0)], BANK_ACCOUNT_ID),
    ).rejects.toMatchObject({ constructor: NothingToBankError, potName: 'Sofa' });
  });

  it('writes nothing when one pot has nothing planned', async () => {
    await bankOneOffs(payments, [BIKE, pot(SOFA.id, 'Sofa', 0)], BANK_ACCOUNT_ID).catch(() => {});

    expect(payments.saved).toEqual([]);
  });

  it('reports a failed write as a banking error, keeping the cause', async () => {
    const cause = new RepositoryError('network down');
    payments.failWith = cause;

    await expect(bankOneOffs(payments, [BIKE], BANK_ACCOUNT_ID)).rejects.toMatchObject({
      constructor: BankOneOffsError,
      cause,
    });
  });
});
