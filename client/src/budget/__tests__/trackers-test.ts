import {
  childrenOf,
  roots,
  takesSubcategories,
  totalAllocated,
  totalIncome,
} from '@/budget/trackers';
import type { CategoryView, IncomeSourceView } from '@/domain/readModels';

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
