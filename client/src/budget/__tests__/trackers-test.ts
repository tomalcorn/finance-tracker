import {
  childrenOf,
  paymentsCountedIn,
  roots,
  takesSubcategories,
  totalAllocated,
  totalIncome,
} from '@/budget/trackers';
import type { CategoryView, IncomeSourceView, PaymentView } from '@/domain/readModels';

function category(id: string, name: string, parentId: string | null = null): CategoryView {
  return {
    id,
    user_id: 'auth0|test',
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: parentId,
    budget: 100,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: 100,
    progress: 0,
    split: 0,
  };
}

describe('roots', () => {
  it('orders the seeded trackers as the app always shows them, then any other by name', () => {
    const categories = [
      category('1', 'Savings'),
      category('2', 'Holidays'),
      category('3', 'Expenses'),
      category('4', 'One-offs'),
      category('5', 'Joint'),
      category('6', 'Groceries', '3'),
    ];

    expect(roots(categories).map((root) => root.name)).toEqual([
      'Expenses',
      'Joint',
      'One-offs',
      'Savings',
      'Holidays',
    ]);
  });
});

describe('childrenOf', () => {
  it('lists one tracker’s subcategories by name', () => {
    const categories = [
      category('1', 'Expenses'),
      category('2', 'Transport', '1'),
      category('3', 'Groceries', '1'),
      category('4', 'Bike', '9'),
    ];

    expect(childrenOf(categories, '1').map((child) => child.name)).toEqual([
      'Groceries',
      'Transport',
    ]);
  });
});

describe('takesSubcategories', () => {
  it.each([
    ['Expenses', true],
    ['One-offs', true],
    ['Joint', false],
    ['Savings', false],
  ])('%s takes subcategories: %p', (name, expected) => {
    expect(takesSubcategories(category('1', name))).toBe(expected);
  });
});

describe('totals', () => {
  it('adds up the income sources for the roll-up month', () => {
    const sources = [{ current_month: 2000 }, { current_month: 450.5 }] as IncomeSourceView[];

    expect(totalIncome(sources)).toBe(2450.5);
  });

  it('adds up the trackers’ budgets', () => {
    expect(totalAllocated([category('1', 'Expenses'), category('2', 'Savings')])).toBe(200);
  });
});

describe('paymentsCountedIn', () => {
  const groceries = category('1', 'Groceries', '9');
  const bike = { ...category('2', 'Bike', '8'), accrual: 'multi_month' as const };

  function payment(id: string, categoryId: string, date: string): PaymentView {
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
      category_id: categoryId,
      income_source_id: null,
      subscription_id: null,
      linked_payment_id: null,
    };
  }

  const payments = [
    payment('old', '1', '2026-10-31'),
    payment('first', '1', '2026-11-01'),
    payment('latest', '1', '2026-11-20'),
    payment('other', '3', '2026-11-05'),
    payment('banked', '2', '2026-03-01'),
  ];

  it('counts a monthly subcategory’s payments this month, newest first', () => {
    expect(paymentsCountedIn(payments, groceries, '2026-11-25').map((p) => p.id)).toEqual([
      'latest',
      'first',
    ]);
  });

  it('counts everything paid into a pot', () => {
    expect(paymentsCountedIn(payments, bike, '2026-11-25').map((p) => p.id)).toEqual(['banked']);
  });
});
