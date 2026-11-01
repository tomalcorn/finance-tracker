import type { PaymentView } from '@/domain/readModels';
import {
  byDay,
  filterPayments,
  monthOf,
  newestFirst,
  shiftMonth,
  signedAmount,
  totals,
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

const NOVEMBER = { month: '2026-11', kind: 'all', search: '' } as const;

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

  it('finds a name whatever its case', () => {
    expect(filterPayments(PAYMENTS, { ...NOVEMBER, search: ' COF ' })).toEqual([COFFEE]);
  });

  it('finds the text it is described by', () => {
    const describe = (row: PaymentView) => (row === SALARY ? 'Monzo' : '');

    expect(filterPayments(PAYMENTS, { ...NOVEMBER, search: 'monzo' }, describe)).toEqual([SALARY]);
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

describe('totals', () => {
  it('adds up what went out and came in', () => {
    expect(totals([SALARY, COFFEE, LUNCH])).toEqual({ out: 11.4, in: 2500 });
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
