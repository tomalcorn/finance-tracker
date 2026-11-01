import {
  fundedTrackers,
  hasPayments,
  incomeCountedIn,
  incomeSourceRow,
  rollUpDate,
} from '@/budget/incomeSources';
import type { CategoryView, IncomeSourceView, PaymentView } from '@/domain/readModels';

const SALARY: IncomeSourceView = {
  id: '2b3c4d5e-0000-4000-8000-000000000001',
  user_id: 'auth0|test',
  name: 'Salary',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  budget_tracker_ids: ['savings', 'expenses'],
  current_month: 2500,
  income_roll_up_period: 'current_month',
};

function payment(id: string, date: string, overrides: Partial<PaymentView> = {}): PaymentView {
  return {
    id,
    user_id: 'auth0|test',
    name: id,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    payment_date: date,
    payment_type: 'income',
    expense: 0,
    income: 100,
    checked: false,
    bank_account_id: 'b',
    category_id: null,
    income_source_id: SALARY.id,
    subscription_id: null,
    linked_payment_id: null,
    ...overrides,
  };
}

const PAYMENTS = [
  payment('october', '2026-10-28'),
  payment('early', '2026-11-01'),
  payment('late', '2026-11-25'),
  payment('other source', '2026-11-05', { income_source_id: 'x' }),
  payment('an expense', '2026-11-06', { payment_type: 'expense' }),
];

describe('rollUpDate', () => {
  it('is today for this month', () => {
    expect(rollUpDate('2026-11-20', 'current_month')).toBe('2026-11-20');
  });

  it('falls in the month before for last month', () => {
    expect(rollUpDate('2026-11-20', 'previous_month')).toBe('2026-10-01');
  });

  it('goes back a year from January', () => {
    expect(rollUpDate('2027-01-03', 'previous_month')).toBe('2026-12-01');
  });
});

describe('incomeCountedIn', () => {
  it('counts the source’s income this month, newest first', () => {
    expect(incomeCountedIn(PAYMENTS, SALARY, '2026-11-26').map((p) => p.id)).toEqual([
      'late',
      'early',
    ]);
  });

  it('counts last month’s when the source rolls up the month before', () => {
    const lastMonth = { ...SALARY, income_roll_up_period: 'previous_month' as const };

    expect(incomeCountedIn(PAYMENTS, lastMonth, '2026-11-26').map((p) => p.id)).toEqual([
      'october',
    ]);
  });
});

describe('hasPayments', () => {
  it('finds a payment booked to the source in any month', () => {
    expect(hasPayments([payment('old', '2020-01-01')], SALARY.id)).toBe(true);
  });

  it('finds none for a source nothing is booked to', () => {
    expect(hasPayments(PAYMENTS, 'unused')).toBe(false);
  });
});

describe('fundedTrackers', () => {
  it('names the trackers a source funds, in the trackers’ order', () => {
    const trackers = [
      { id: 'expenses', name: 'Expenses' },
      { id: 'joint', name: 'Joint' },
      { id: 'savings', name: 'Savings' },
    ] as CategoryView[];

    expect(fundedTrackers(SALARY, trackers)).toEqual(['Expenses', 'Savings']);
  });
});

describe('incomeSourceRow', () => {
  it('keeps the edited source’s id, with the new name and trackers', () => {
    expect(incomeSourceRow({ name: ' Pay ', trackerIds: ['savings'] }, SALARY)).toMatchObject({
      id: SALARY.id,
      name: 'Pay',
      budget_tracker_ids: ['savings'],
    });
  });
});
