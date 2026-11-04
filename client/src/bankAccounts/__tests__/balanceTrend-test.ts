import { dailyBalances, sampled } from '@/bankAccounts/balanceTrend';
import type { BankAccountView, PaymentView } from '@/domain/readModels';

const MONZO_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const AMEX_ID = '3c4d5e6f-0000-4000-8000-000000000002';
const NOW = '2026-11-03';

const OWNED = {
  user_id: 'auth0|test',
  name: 'Sample',
  _created_at: '2026-01-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
} as const;

function account(overrides: Partial<BankAccountView> = {}): BankAccountView {
  return {
    ...OWNED,
    id: MONZO_ID,
    starting_balance: 0,
    current_balance: 100,
    ...overrides,
  };
}

function payment(date: string, net: number, bankAccountId = MONZO_ID): PaymentView {
  return {
    ...OWNED,
    id: '4d5e6f70-0000-4000-8000-000000000001',
    payment_date: date,
    payment_type: net < 0 ? 'expense' : 'income',
    expense: Math.max(-net, 0),
    income: Math.max(net, 0),
    checked: false,
    bank_account_id: bankAccountId,
    category_id: null,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

function balances(...args: Parameters<typeof dailyBalances>): number[] {
  return dailyBalances(...args).map((point) => point.balance);
}

describe('dailyBalances', () => {
  it('ends on the current balance', () => {
    expect(balances(account(), [payment('2026-10-01', -30)], NOW).at(-1)).toBe(100);
  });

  it('ends today', () => {
    expect(dailyBalances(account(), [], NOW).at(-1)?.date).toBe(NOW);
  });

  it('starts the day before the window', () => {
    expect(dailyBalances(account(), [], NOW)[0]?.date).toBe('2026-08-02');
  });

  it('starts before the payments it covers', () => {
    expect(balances(account(), [payment('2026-10-01', -30)], NOW)[0]).toBe(130);
  });

  it('moves on the day of the payment', () => {
    const history = balances(
      account({ _created_at: '2026-11-01T09:30:12+00:00' }),
      [payment('2026-11-02', -30)],
      NOW,
    );

    expect(history).toEqual([130, 130, 100, 100]);
  });

  it('adds up several payments on one day', () => {
    const history = balances(
      account({ _created_at: `${NOW}T09:30:12+00:00` }),
      [payment(NOW, -30), payment(NOW, 10)],
      NOW,
    );

    expect(history).toEqual([120, 100]);
  });

  it('leaves out payments before the window', () => {
    expect(new Set(balances(account(), [payment('2026-07-01', 500)], NOW))).toEqual(new Set([100]));
  });

  it('leaves out payments still to come', () => {
    expect(new Set(balances(account(), [payment('2026-11-04', -30)], NOW))).toEqual(new Set([100]));
  });

  it('leaves out other accounts', () => {
    const history = balances(account(), [payment('2026-10-01', -30, AMEX_ID)], NOW);

    expect(new Set(history)).toEqual(new Set([100]));
  });

  it('starts a young account the day before it was created', () => {
    const history = dailyBalances(account({ _created_at: '2026-10-12T09:30:12+00:00' }), [], NOW);

    expect(history[0]?.date).toBe('2026-10-11');
  });

  it('starts a young account at an earlier payment backdated onto it', () => {
    const history = dailyBalances(
      account({ _created_at: '2026-10-12T09:30:12+00:00' }),
      [payment('2026-09-20', -30)],
      NOW,
    );

    expect(history[0]?.date).toBe('2026-09-19');
  });

  it('draws an account created today as a flat pair', () => {
    const history = balances(account({ _created_at: `${NOW}T09:30:12+00:00` }), [], NOW);

    expect(history).toEqual([100, 100]);
  });

  it('copes with an account stamped ahead of the local date', () => {
    const history = balances(account({ _created_at: '2026-11-04T00:30:00+00:00' }), [], NOW);

    expect(history).toEqual([100, 100]);
  });

  it('rounds away floating point noise', () => {
    const history = balances(
      account(),
      [payment('2026-10-01', 0.1), payment('2026-10-02', 0.2), payment('2026-10-03', -0.3)],
      NOW,
    );

    expect(history[0]).toBe(100);
  });
});

describe('sampled', () => {
  const quarter = Array.from({ length: 94 }, (_, index) => index);

  it('takes about one value a week', () => {
    expect(sampled(quarter)).toHaveLength(14);
  });

  it('keeps the first value', () => {
    expect(sampled(quarter)[0]).toBe(0);
  });

  it('keeps the last value', () => {
    expect(sampled(quarter).at(-1)).toBe(93);
  });

  it('keeps both ends of a series shorter than a week', () => {
    expect(sampled([1, 2, 3, 4])).toEqual([1, 4]);
  });
});
