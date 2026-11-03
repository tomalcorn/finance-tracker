import type { SubscriptionView } from '@/domain/readModels';
import {
  subscriptionDraftErrors,
  subscriptionDraftOf,
  subscriptionRow,
  type SubscriptionDraft,
} from '@/subscriptions/subscriptionDraft';

const DRAFT: SubscriptionDraft = {
  name: 'Netflix',
  amount: '9.99',
  cadence: 'monthly',
  bankAccountId: 'bank',
  categoryId: 'fun',
  startDate: '2026-11-01',
  endDate: '',
  isActive: true,
  jointBankAccountId: null,
  jointIncomeSourceId: null,
};

const CONTRIBUTION: SubscriptionView = {
  id: '5e6f7081-0000-4000-8000-000000000001',
  user_id: 'auth0|test',
  name: 'To joint',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  amount: 500,
  cadence: 'monthly',
  bank_account_id: 'bank',
  category_id: 'joint-tracker',
  start_date: '2026-01-01',
  end_date: null,
  is_active: true,
  monthly_cost: 500,
  joint_income_source_id: 'joint-source',
  joint_bank_account_id: 'joint-bank',
};

describe('subscriptionDraftOf', () => {
  it('starts a new one monthly, active and from today', () => {
    expect(subscriptionDraftOf(null, '2026-11-01')).toEqual({
      name: '',
      amount: '',
      cadence: 'monthly',
      bankAccountId: null,
      categoryId: null,
      startDate: '2026-11-01',
      endDate: '',
      isActive: true,
      jointBankAccountId: null,
      jointIncomeSourceId: null,
    });
  });

  it('fills in an existing one', () => {
    expect(subscriptionDraftOf(CONTRIBUTION, '2026-11-01')).toEqual({
      name: 'To joint',
      amount: '500.00',
      cadence: 'monthly',
      bankAccountId: 'bank',
      categoryId: 'joint-tracker',
      startDate: '2026-01-01',
      endDate: '',
      isActive: true,
      jointBankAccountId: 'joint-bank',
      jointIncomeSourceId: 'joint-source',
    });
  });
});

describe('subscriptionDraftErrors', () => {
  it('passes a complete draft', () => {
    expect(subscriptionDraftErrors(DRAFT, false)).toEqual({});
  });

  it.each([
    ['a name', { name: ' ' }, 'name'],
    ['an amount', { amount: '' }, 'amount'],
    ['an amount that is one', { amount: 'lots' }, 'amount'],
    ['an amount above zero', { amount: '0' }, 'amount'],
    ['a bank account', { bankAccountId: null }, 'bankAccountId'],
    ['a real start date', { startDate: '2026-02-30' }, 'startDate'],
    ['a real end date', { endDate: 'soon' }, 'endDate'],
    ['an end not before the start', { endDate: '2026-10-31' }, 'endDate'],
  ])('asks for %s', (_what, change, field) => {
    expect(Object.keys(subscriptionDraftErrors({ ...DRAFT, ...change }, false))).toEqual([field]);
  });

  it('allows no end date', () => {
    expect(subscriptionDraftErrors({ ...DRAFT, endDate: '  ' }, false)).toEqual({});
  });

  it('allows ending on the day it starts', () => {
    expect(subscriptionDraftErrors({ ...DRAFT, endDate: DRAFT.startDate }, false)).toEqual({});
  });

  it('asks a contribution for its joint fields', () => {
    expect(Object.keys(subscriptionDraftErrors(DRAFT, true))).toEqual([
      'jointBankAccountId',
      'jointIncomeSourceId',
    ]);
  });
});

describe('subscriptionRow', () => {
  it('saves an ordinary one against its chosen category', () => {
    expect(subscriptionRow(DRAFT, null, false, 'joint-tracker')).toEqual({
      name: 'Netflix',
      amount: 9.99,
      cadence: 'monthly',
      bank_account_id: 'bank',
      start_date: '2026-11-01',
      end_date: null,
      is_active: true,
      category_id: 'fun',
    });
  });

  it('books a new contribution against the Joint tracker, not a chosen category', () => {
    const draft = { ...DRAFT, jointBankAccountId: 'jb', jointIncomeSourceId: 'js' };

    expect(subscriptionRow(draft, null, true, 'joint-tracker')).toEqual(
      expect.objectContaining({
        category_id: 'joint-tracker',
        joint_bank_account_id: 'jb',
        joint_income_source_id: 'js',
      }),
    );
  });

  it('keeps the joint columns of a leftover contribution edited in the ordinary list', () => {
    const row = subscriptionRow(
      subscriptionDraftOf(CONTRIBUTION, '2026-11-01'),
      CONTRIBUTION,
      false,
      null,
    );

    expect(row).toEqual(
      expect.objectContaining({
        joint_bank_account_id: 'joint-bank',
        joint_income_source_id: 'joint-source',
      }),
    );
  });
});
