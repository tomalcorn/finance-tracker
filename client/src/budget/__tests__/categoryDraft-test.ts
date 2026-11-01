import {
  categoryDraftErrors,
  categoryDraftOf,
  categoryDraftRow,
  trackerBudgetError,
  type CategoryDraft,
} from '@/budget/categoryDraft';
import type { CategoryView } from '@/domain/readModels';

const ROOT: CategoryView = {
  id: '1a2b3c4d-0000-4000-8000-000000000001',
  user_id: 'auth0|test',
  name: 'One-offs',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  parent_id: null,
  budget: 300,
  accrual: 'monthly',
  cost: 0,
  starting_balance: 0,
  accrued: 0,
  remaining: 300,
  progress: 0,
  split: 10,
};

const POT: CategoryView = {
  ...ROOT,
  id: '1a2b3c4d-0000-4000-8000-000000000002',
  name: 'Bike',
  parent_id: ROOT.id,
  accrual: 'multi_month',
  budget: 50,
  cost: 600,
  starting_balance: 100,
};

const DRAFT: CategoryDraft = { name: 'Bike', budget: '50', cost: '600', startingBalance: '' };

describe('categoryDraftErrors', () => {
  it('accepts a complete pot', () => {
    expect(categoryDraftErrors(DRAFT, true)).toEqual({});
  });

  it('needs a name', () => {
    expect(categoryDraftErrors({ ...DRAFT, name: ' ' }, true)).toHaveProperty('name');
  });

  it('refuses a negative budget', () => {
    expect(categoryDraftErrors({ ...DRAFT, budget: '-5' }, false)).toHaveProperty('budget');
  });

  it('checks a pot’s cost', () => {
    expect(categoryDraftErrors({ ...DRAFT, cost: 'lots' }, true)).toHaveProperty('cost');
  });

  it('ignores a pot’s fields on a monthly subcategory', () => {
    expect(categoryDraftErrors({ ...DRAFT, cost: 'lots' }, false)).toEqual({});
  });
});

describe('categoryDraftRow', () => {
  it('files a new pot under its tracker, accruing across months', () => {
    expect(categoryDraftRow(DRAFT, ROOT, true, null)).toMatchObject({
      parent_id: ROOT.id,
      accrual: 'multi_month',
      budget: 50,
      cost: 600,
      starting_balance: 0,
    });
  });

  it('keeps the edited subcategory’s id', () => {
    expect(categoryDraftRow(DRAFT, ROOT, true, POT).id).toBe(POT.id);
  });

  it('makes a monthly subcategory reset each month', () => {
    expect(categoryDraftRow(DRAFT, ROOT, false, null).accrual).toBe('monthly');
  });
});

describe('categoryDraftOf', () => {
  it('fills the form from a pot', () => {
    expect(categoryDraftOf(POT)).toEqual({
      name: 'Bike',
      budget: '50.00',
      cost: '600.00',
      startingBalance: '100.00',
    });
  });
});

describe('trackerBudgetError', () => {
  it.each([
    ['', true],
    ['-1', true],
    ['abc', true],
    ['0', false],
    ['1,200', false],
  ])('%p is an error: %p', (text, isError) => {
    expect(trackerBudgetError(text) !== undefined).toBe(isError);
  });
});
