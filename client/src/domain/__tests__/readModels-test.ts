import type { z } from 'zod';

import {
  BankAccountViewSchema,
  CategoryViewSchema,
  IncomeSourceViewSchema,
  JointAccountMemberViewSchema,
  JointAccountViewSchema,
  PaymentViewSchema,
  QuickButtonViewSchema,
  SubscriptionViewSchema,
  UserSettingsViewSchema,
} from '@/domain/readModels';

const ID = '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01';
const OTHER_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';
const JOINT_ACCOUNT_ID = '9a3d6e1f-4c2b-4f7a-8e5d-1b6c3a9f2e08';

const BASE = {
  id: ID,
  user_id: 'auth0|65f0c2a1b3d4e5f6a7b8c9d0',
  name: 'Groceries',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
};

const VIEW_ROWS: [string, z.ZodType, Record<string, unknown>][] = [
  [
    'bank_accounts_view',
    BankAccountViewSchema,
    { ...BASE, starting_balance: 1200, current_balance: 843.5 },
  ],
  [
    'categories_view',
    CategoryViewSchema,
    {
      ...BASE,
      parent_id: OTHER_ID,
      budget: 300,
      accrual: 'multi_month',
      cost: 1500,
      starting_balance: 200,
      accrued: 650,
      remaining: 850,
      progress: 43.33,
      split: 120,
    },
  ],
  [
    'income_sources_view',
    IncomeSourceViewSchema,
    {
      ...BASE,
      budget_tracker_ids: [OTHER_ID],
      current_month: 2500,
      income_roll_up_period: 'previous_month',
    },
  ],
  [
    'subscriptions_view',
    SubscriptionViewSchema,
    {
      ...BASE,
      amount: 120,
      cadence: 'quarterly',
      bank_account_id: OTHER_ID,
      category_id: null,
      start_date: '2026-01-15',
      end_date: null,
      is_active: true,
      monthly_cost: 40,
      joint_income_source_id: null,
      joint_bank_account_id: null,
    },
  ],
  [
    'payments',
    PaymentViewSchema,
    {
      ...BASE,
      ownership_type: 'joint',
      joint_account_id: JOINT_ACCOUNT_ID,
      payment_date: '2026-10-03',
      payment_type: 'expense',
      expense: -12.5,
      income: 0,
      checked: false,
      bank_account_id: OTHER_ID,
      category_id: OTHER_ID,
      income_source_id: null,
      subscription_id: null,
      linked_payment_id: null,
    },
  ],
  [
    'quick_buttons',
    QuickButtonViewSchema,
    {
      ...BASE,
      mode: 'prompt',
      payment_name: null,
      expense: null,
      bank_account_id: null,
      category_id: OTHER_ID,
      icon: '☕',
      display_order: 2,
    },
  ],
  [
    'user_settings',
    UserSettingsViewSchema,
    { ...BASE, name: '', income_roll_up_period: 'current_month' },
  ],
  ['joint_accounts', JointAccountViewSchema, { id: JOINT_ACCOUNT_ID, name: 'Household' }],
  [
    'joint_account_members',
    JointAccountMemberViewSchema,
    { id: ID, joint_account_id: JOINT_ACCOUNT_ID, user_id: 'auth0|65f0c2a1b3d4e5f6a7b8c9d0' },
  ],
];

describe('read models', () => {
  it.each(VIEW_ROWS)('parse a %s row', (_view, schema, row) => {
    expect(schema.parse(row)).toEqual(row);
  });

  it.each(VIEW_ROWS.filter(([, , row]) => 'ownership_type' in row))(
    'reject a %s row missing a required column',
    (_view, schema, row) => {
      const { name: _name, ...missingName } = row;

      expect(schema.safeParse(missingName).success).toBe(false);
    },
  );

  it('rejects a joint row with no joint account', () => {
    const [, schema, row] = VIEW_ROWS[0]!;

    expect(schema.safeParse({ ...row, ownership_type: 'joint' }).success).toBe(false);
  });

  it('leaves a category over budget unbounded', () => {
    const [, , row] = VIEW_ROWS[1]!;

    expect(CategoryViewSchema.parse({ ...row, progress: 206 }).progress).toBe(206);
  });
});
