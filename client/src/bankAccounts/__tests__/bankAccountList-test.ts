import { byName, isInUse, totalBalance } from '@/bankAccounts/bankAccountList';
import type { BankAccountView, PaymentView, SubscriptionView } from '@/domain/readModels';

const FIELDS = {
  user_id: 'auth0|test',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
} as const;

function account(name: string, currentBalance: number): BankAccountView {
  return { ...FIELDS, id: name, name, starting_balance: 0, current_balance: currentBalance };
}

function payment(bankAccountId: string): PaymentView {
  return {
    ...FIELDS,
    id: `payment-${bankAccountId}`,
    name: 'Coffee',
    payment_date: '2026-11-01',
    payment_type: 'expense',
    expense: 3,
    income: 0,
    checked: false,
    bank_account_id: bankAccountId,
    category_id: null,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

function subscription(overrides: Partial<SubscriptionView>): SubscriptionView {
  return {
    ...FIELDS,
    id: 'subscription',
    name: 'Netflix',
    amount: 10,
    cadence: 'monthly',
    bank_account_id: 'other',
    category_id: null,
    start_date: '2026-01-01',
    end_date: null,
    is_active: true,
    monthly_cost: 10,
    joint_income_source_id: null,
    joint_bank_account_id: null,
    ...overrides,
  };
}

describe('byName', () => {
  it('puts the accounts in name order', () => {
    const sorted = byName([account('Monzo', 0), account('Amex', 0)]);

    expect(sorted.map((row) => row.name)).toEqual(['Amex', 'Monzo']);
  });
});

describe('totalBalance', () => {
  it('adds up the current balances', () => {
    expect(totalBalance([account('Monzo', 100), account('Saver', 50.5)])).toBe(150.5);
  });

  it('counts an overdrawn account against the rest', () => {
    expect(totalBalance([account('Monzo', 100), account('Amex', -30)])).toBe(70);
  });

  it('is zero with no accounts', () => {
    expect(totalBalance([])).toBe(0);
  });
});

describe('isInUse', () => {
  it('is false when nothing uses the account', () => {
    expect(isInUse('a', [payment('b')], [subscription({})])).toBe(false);
  });

  it('is true with a payment on the account', () => {
    expect(isInUse('a', [payment('a')], [])).toBe(true);
  });

  it('is true with a subscription paid from the account', () => {
    expect(isInUse('a', [], [subscription({ bank_account_id: 'a' })])).toBe(true);
  });

  it('is true with a contribution arriving in the account', () => {
    expect(isInUse('a', [], [subscription({ joint_bank_account_id: 'a' })])).toBe(true);
  });
});
