import { balanceTrend, describeChange, type BalanceTrend } from '@/bankAccounts/balanceTrend';
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

function trend(overrides: Partial<BalanceTrend> = {}): BalanceTrend {
  return { from: '2026-08-03', partial: false, balances: [0, 0], change: 0, ...overrides };
}

describe('balanceTrend', () => {
  it('ends on the current balance', () => {
    const { balances } = balanceTrend(account(), [payment('2026-10-01', -30)], NOW);

    expect(balances.at(-1)).toBe(100);
  });

  it('starts before the payments it covers', () => {
    const { balances } = balanceTrend(account(), [payment('2026-10-01', -30)], NOW);

    expect(balances[0]).toBe(130);
  });

  it('takes about one balance a week', () => {
    const { balances } = balanceTrend(account(), [], NOW);

    expect(balances).toHaveLength(14);
  });

  it('shows a payment from the next balance taken', () => {
    const { balances } = balanceTrend(account(), [payment('2026-10-01', -30)], NOW);

    expect(new Set(balances)).toEqual(new Set([130, 100]));
  });

  it('keeps both ends of a history shorter than a week', () => {
    const { balances } = balanceTrend(
      account({ _created_at: '2026-11-01T09:30:12+00:00' }),
      [payment('2026-11-02', -30)],
      NOW,
    );

    expect(balances).toEqual([130, 100]);
  });

  it('reports the change across the window', () => {
    const { change } = balanceTrend(
      account(),
      [payment('2026-10-01', -30), payment('2026-10-02', 80)],
      NOW,
    );

    expect(change).toBe(50);
  });

  it('leaves out payments before the window', () => {
    const { change } = balanceTrend(account(), [payment('2026-07-01', 500)], NOW);

    expect(change).toBe(0);
  });

  it('leaves out payments still to come', () => {
    const { change } = balanceTrend(account(), [payment('2026-11-04', -30)], NOW);

    expect(change).toBe(0);
  });

  it('leaves out other accounts', () => {
    const { change } = balanceTrend(account(), [payment('2026-10-01', -30, AMEX_ID)], NOW);

    expect(change).toBe(0);
  });

  it('goes back three months', () => {
    const { from } = balanceTrend(account(), [], NOW);

    expect(from).toBe('2026-08-03');
  });

  it('starts a young account on the day it was created', () => {
    const { from } = balanceTrend(account({ _created_at: '2026-10-12T09:30:12+00:00' }), [], NOW);

    expect(from).toBe('2026-10-12');
  });

  it('starts a young account at an earlier payment backdated onto it', () => {
    const { from } = balanceTrend(
      account({ _created_at: '2026-10-12T09:30:12+00:00' }),
      [payment('2026-09-20', -30)],
      NOW,
    );

    expect(from).toBe('2026-09-20');
  });

  it('marks a young account as partial', () => {
    const { partial } = balanceTrend(
      account({ _created_at: '2026-10-12T09:30:12+00:00' }),
      [],
      NOW,
    );

    expect(partial).toBe(true);
  });

  it('draws an account created today as a flat pair', () => {
    const { balances } = balanceTrend(account({ _created_at: `${NOW}T09:30:12+00:00` }), [], NOW);

    expect(balances).toEqual([100, 100]);
  });

  it('copes with an account stamped ahead of the local date', () => {
    const { balances } = balanceTrend(
      account({ _created_at: '2026-11-04T00:30:00+00:00' }),
      [],
      NOW,
    );

    expect(balances).toEqual([100, 100]);
  });

  it('rounds away floating point noise', () => {
    const { change } = balanceTrend(
      account(),
      [payment('2026-10-01', 0.1), payment('2026-10-02', 0.2), payment('2026-10-03', -0.3)],
      NOW,
    );

    expect(change).toBe(0);
  });
});

describe('describeChange', () => {
  it('signs a rise', () => {
    expect(describeChange(trend({ change: 50.5 }))).toBe('+£50.50 in 3 months');
  });

  it('signs a fall', () => {
    expect(describeChange(trend({ change: -30 }))).toBe('-£30 in 3 months');
  });

  it('leaves the pence off a large change', () => {
    expect(describeChange(trend({ change: 1004.5 }))).toBe('+£1,005 in 3 months');
  });

  it('says when nothing moved', () => {
    expect(describeChange(trend())).toBe('Flat in 3 months');
  });

  it('dates a young account', () => {
    expect(describeChange(trend({ partial: true, from: '2026-10-12', change: 5 }))).toBe(
      '+£5 since 12 Oct',
    );
  });
});
