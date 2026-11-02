import type { BankAccountView, PaymentView } from '@/domain/readModels';
import {
  byCategory,
  byDay,
  closingBalances,
  filterPayments,
  monthOf,
  newestFirst,
  shiftMonth,
  signedAmount,
  totals,
  uncheckedDays,
} from '@/payments/paymentList';

function payment(id: string, date: string, overrides: Partial<PaymentView> = {}): PaymentView {
  return {
    id,
    user_id: 'auth0|test',
    name: id,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    payment_date: date,
    payment_type: 'expense',
    expense: 10,
    income: 0,
    checked: false,
    bank_account_id: 'b',
    category_id: null,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
    ...overrides,
  };
}

const SALARY = payment('Salary', '2026-11-01', {
  payment_type: 'income',
  expense: 0,
  income: 2500,
});
const COFFEE = payment('Coffee', '2026-11-03', { expense: 3.4 });
const LUNCH = payment('Lunch', '2026-11-03', {
  expense: 8,
  _created_at: '2026-11-03T12:00:00+00:00',
});
const RENT = payment('Rent', '2026-10-28', { expense: 900 });
const PAYMENTS = [SALARY, COFFEE, RENT, LUNCH];

const NOVEMBER = { month: '2026-11', kind: 'all' } as const;

describe('signedAmount', () => {
  it('is negative for money out', () => {
    expect(signedAmount(COFFEE)).toBe(-3.4);
  });

  it('is positive for money in', () => {
    expect(signedAmount(SALARY)).toBe(2500);
  });
});

describe('newestFirst', () => {
  it('puts the later date first', () => {
    expect([RENT, COFFEE].sort(newestFirst)).toEqual([COFFEE, RENT]);
  });

  it('puts the later-added first within a day', () => {
    expect([COFFEE, LUNCH].sort(newestFirst)).toEqual([LUNCH, COFFEE]);
  });
});

describe('filterPayments', () => {
  it('keeps the month’s payments, newest first', () => {
    expect(filterPayments(PAYMENTS, NOVEMBER)).toEqual([LUNCH, COFFEE, SALARY]);
  });

  it('keeps only money out for expenses', () => {
    expect(filterPayments(PAYMENTS, { ...NOVEMBER, kind: 'expense' })).toEqual([LUNCH, COFFEE]);
  });

  it('keeps only money in for income', () => {
    expect(filterPayments(PAYMENTS, { ...NOVEMBER, kind: 'income' })).toEqual([SALARY]);
  });

  it('keeps only what the check accepts', () => {
    expect(filterPayments(PAYMENTS, NOVEMBER, (row) => row === SALARY)).toEqual([SALARY]);
  });
});

describe('byDay', () => {
  it('groups a day’s payments together, in order', () => {
    expect(byDay([LUNCH, COFFEE, SALARY]).map((day) => day.payments)).toEqual([
      [LUNCH, COFFEE],
      [SALARY],
    ]);
  });

  it('nets each day', () => {
    expect(byDay([LUNCH, COFFEE, SALARY]).map((day) => day.net)).toEqual([-11.4, 2500]);
  });
});

describe('byCategory', () => {
  const GROCERIES = payment('Groceries', '2026-11-02', { expense: 40, category_id: 'groceries' });
  const UNFILED = payment('Unfiled', '2026-11-04', { expense: 5 });

  it('puts the category spent on most first', () => {
    expect(byCategory([UNFILED, GROCERIES]).map((group) => group.categoryId)).toEqual([
      'groceries',
      null,
    ]);
  });

  it('adds up what each category spent', () => {
    expect(byCategory([GROCERIES, LUNCH, UNFILED]).map((group) => group.total)).toEqual([40, 13]);
  });

  it('keeps the payments’ order within a category', () => {
    expect(byCategory([LUNCH, COFFEE])[0]?.payments).toEqual([LUNCH, COFFEE]);
  });

  it('leaves income out', () => {
    expect(byCategory([SALARY])).toEqual([]);
  });
});

describe('totals', () => {
  it('adds up what went out and came in', () => {
    expect(totals([SALARY, COFFEE, LUNCH])).toEqual({ out: 11.4, in: 2500 });
  });
});

describe('closingBalances', () => {
  function account(id: string, name: string, startingBalance: number): BankAccountView {
    return {
      id,
      user_id: 'auth0|test',
      name,
      _created_at: '2026-10-01T09:30:12.345678+00:00',
      ownership_type: 'personal',
      joint_account_id: null,
      starting_balance: startingBalance,
      current_balance: 0,
    };
  }

  const ACCOUNTS = [account('b', 'Santander', 100), account('amex', 'AMEX', 50)];
  const ON_AMEX = payment('Shoes', '2026-11-03', { expense: 20, bank_account_id: 'amex' });
  const LATER = payment('Later', '2026-11-05', { expense: 7 });
  const EVERY_PAYMENT = [RENT, COFFEE, LUNCH, SALARY, ON_AMEX, LATER];

  it('adds every payment up to the end of the day to the starting balance', () => {
    const day = { date: '2026-11-03', payments: [COFFEE], net: -3.4 };

    expect(closingBalances(day, ACCOUNTS, EVERY_PAYMENT)).toEqual([
      { name: 'Santander', balance: 100 - 900 + 2500 - 3.4 - 8 },
    ]);
  });

  it('shows only the accounts in the day as listed', () => {
    const day = { date: '2026-11-03', payments: [ON_AMEX], net: -20 };

    expect(closingBalances(day, ACCOUNTS, EVERY_PAYMENT).map((it) => it.name)).toEqual(['AMEX']);
  });

  it('lists accounts in name order', () => {
    const day = { date: '2026-11-03', payments: [COFFEE, ON_AMEX], net: -23.4 };

    expect(closingBalances(day, ACCOUNTS, EVERY_PAYMENT).map((it) => it.name)).toEqual([
      'AMEX',
      'Santander',
    ]);
  });

  it('leaves out an account it doesn’t know', () => {
    const day = { date: '2026-11-03', payments: [COFFEE], net: -3.4 };

    expect(closingBalances(day, [], EVERY_PAYMENT)).toEqual([]);
  });
});

describe('uncheckedDays', () => {
  it('counts each day once', () => {
    expect(uncheckedDays([COFFEE, LUNCH, SALARY], '2026-11-30')).toBe(2);
  });

  it('counts a day as checked once any of its payments is ticked', () => {
    expect(uncheckedDays([{ ...COFFEE, checked: true }, LUNCH], '2026-11-30')).toBe(0);
  });

  it('leaves out days still to come', () => {
    expect(uncheckedDays([COFFEE, SALARY], '2026-11-02')).toBe(1);
  });
});

describe('monthOf', () => {
  it('is the year and month of a date', () => {
    expect(monthOf('2026-11-03')).toBe('2026-11');
  });
});

describe('shiftMonth', () => {
  it('steps back into the year before', () => {
    expect(shiftMonth('2026-01', -1)).toBe('2025-12');
  });

  it('steps on into the year after', () => {
    expect(shiftMonth('2026-12', 1)).toBe('2027-01');
  });
});
