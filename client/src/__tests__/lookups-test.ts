import type { CategoryView } from '@/domain/readModels';
import { categoryOptions, nameOptions } from '@/lookups';

const EXPENSES_ID = '1a2b3c4d-0000-4000-8000-000000000001';
const SAVINGS_ID = '1a2b3c4d-0000-4000-8000-000000000002';

function category(id: string, name: string, parentId: string | null): CategoryView {
  return {
    id,
    user_id: 'auth0|test',
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: parentId,
    budget: 0,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: 0,
    progress: 0,
    split: 0,
  } as CategoryView;
}

describe('categoryOptions', () => {
  it('lists each tracker followed by its subcategories, every level by name', () => {
    const categories = [
      category('1a2b3c4d-0000-4000-8000-000000000003', 'Transport', EXPENSES_ID),
      category(SAVINGS_ID, 'Savings', null),
      category('1a2b3c4d-0000-4000-8000-000000000004', 'Groceries', EXPENSES_ID),
      category(EXPENSES_ID, 'Expenses', null),
    ];

    expect(categoryOptions(categories).map((option) => option.label)).toEqual([
      'Expenses',
      'Expenses - Groceries',
      'Expenses - Transport',
      'Savings',
    ]);
  });

  it('keeps a subcategory whose tracker is missing, by its own name, at the end', () => {
    const categories = [
      category('1a2b3c4d-0000-4000-8000-000000000005', 'Stray', SAVINGS_ID),
      category(EXPENSES_ID, 'Expenses', null),
    ];

    expect(categoryOptions(categories).map((option) => option.label)).toEqual([
      'Expenses',
      'Stray',
    ]);
  });
});

describe('nameOptions', () => {
  it('lists rows by name', () => {
    expect(
      nameOptions([
        { id: 'b', name: 'Savings' },
        { id: 'a', name: 'Current' },
      ]),
    ).toEqual([
      { value: 'a', label: 'Current' },
      { value: 'b', label: 'Savings' },
    ]);
  });
});
