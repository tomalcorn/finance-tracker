import { changedRows, draftBudget, editErrors } from '@/budget/rebalance';
import type { CategoryView } from '@/domain/readModels';

function tracker(id: string, budget: number): CategoryView {
  return {
    id,
    user_id: 'auth0|test',
    name: id,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: null,
    budget,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: budget,
    progress: 0,
    split: 0,
  };
}

const EXPENSES = tracker('expenses', 350);
const SAVINGS = tracker('savings', 740);

describe('draftBudget', () => {
  it('takes a typed budget', () => {
    expect(draftBudget(SAVINGS, { savings: '1,000' })).toBe(1000);
  });

  it('keeps the saved budget while the typed one does not read', () => {
    expect(draftBudget(SAVINGS, { savings: '10x' })).toBe(740);
  });

  it('keeps the saved budget when nothing was typed', () => {
    expect(draftBudget(SAVINGS, {})).toBe(740);
  });
});

describe('editErrors', () => {
  it('reports each edit that is not a budget', () => {
    expect(Object.keys(editErrors({ expenses: '-5', savings: '700' }))).toEqual(['expenses']);
  });
});

describe('changedRows', () => {
  it('saves only the trackers whose budget changed', () => {
    expect(
      changedRows([EXPENSES, SAVINGS], { expenses: '350.00', savings: '800' }).map((row) => [
        row.id,
        row.budget,
      ]),
    ).toEqual([['savings', 800]]);
  });
});
