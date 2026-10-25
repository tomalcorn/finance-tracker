import type { z } from 'zod';

import {
  CategorySchema,
  PaymentSchema,
  QuickButtonSchema,
  SubscriptionSchema,
  today,
} from '@/domain/entities';

const USER_ID = 'auth0|65f0c2a1b3d4e5f6a7b8c9d0';
const ID = '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';
const JOINT_ID = '9a3d6e1f-4c2b-4f7a-8e5d-1b6c3a9f2e08';

/** The path of each issue reported by `schema` for `input`. */
function issuePaths(schema: z.ZodType, input: unknown): string[] {
  const result = schema.safeParse(input);
  return result.success ? [] : result.error.issues.map((issue) => issue.path.join('.'));
}

describe('defaults', () => {
  it('give a new entity an id', () => {
    expect(
      QuickButtonSchema.parse({ user_id: USER_ID, name: 'Coffee', mode: 'prompt' }).id,
    ).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('date a new payment today', () => {
    const payment = PaymentSchema.parse({
      user_id: USER_ID,
      payment_type: 'income',
      bank_account_id: BANK_ACCOUNT_ID,
    });

    expect(payment.payment_date).toBe(today());
  });
});

describe('ownership', () => {
  it('requires a joint account for a joint row', () => {
    expect(
      issuePaths(QuickButtonSchema, {
        user_id: USER_ID,
        name: 'Coffee',
        mode: 'prompt',
        ownership_type: 'joint',
      }),
    ).toEqual(['joint_account_id']);
  });
});

describe('CategorySchema', () => {
  it('rejects a category that is its own parent', () => {
    expect(issuePaths(CategorySchema, { id: ID, user_id: USER_ID, parent_id: ID })).toEqual([
      'parent_id',
    ]);
  });

  it('rejects a root that accrues across months', () => {
    expect(issuePaths(CategorySchema, { user_id: USER_ID, accrual: 'multi_month' })).toEqual([
      'accrual',
    ]);
  });

  it('rejects a negative budget', () => {
    expect(issuePaths(CategorySchema, { user_id: USER_ID, budget: -1 })).toEqual(['budget']);
  });
});

describe('SubscriptionSchema', () => {
  const subscription = { user_id: USER_ID, bank_account_id: BANK_ACCOUNT_ID };

  it('names the joint field a half-set contribution is missing', () => {
    expect(issuePaths(SubscriptionSchema, { ...subscription, joint_income_source_id: ID })).toEqual(
      ['joint_bank_account_id'],
    );
  });

  it('rejects a joint-owned contribution', () => {
    expect(
      issuePaths(SubscriptionSchema, {
        ...subscription,
        ownership_type: 'joint',
        joint_account_id: JOINT_ID,
        joint_income_source_id: ID,
        joint_bank_account_id: BANK_ACCOUNT_ID,
      }),
    ).toEqual(['joint_income_source_id']);
  });
});

describe('PaymentSchema', () => {
  it('picks the income branch by payment_type', () => {
    const payment = PaymentSchema.parse({
      user_id: USER_ID,
      payment_type: 'income',
      bank_account_id: BANK_ACCOUNT_ID,
      income_source_id: ID,
    });

    expect(payment).toMatchObject({ payment_type: 'income', income_source_id: ID });
  });

  it('rejects an unknown payment_type', () => {
    expect(
      issuePaths(PaymentSchema, {
        user_id: USER_ID,
        payment_type: 'transfer',
        bank_account_id: BANK_ACCOUNT_ID,
      }),
    ).toEqual(['payment_type']);
  });
});

describe('QuickButtonSchema', () => {
  it('names what a log button is missing', () => {
    expect(
      issuePaths(QuickButtonSchema, { user_id: USER_ID, name: 'Coffee', mode: 'log' }),
    ).toEqual(['expense', 'bank_account_id']);
  });

  it('accepts a prompt button with no preset', () => {
    expect(
      issuePaths(QuickButtonSchema, { user_id: USER_ID, name: 'Coffee', mode: 'prompt' }),
    ).toEqual([]);
  });

  it('accepts a negative amount', () => {
    expect(
      issuePaths(QuickButtonSchema, {
        user_id: USER_ID,
        name: 'Refund',
        expense: -20,
        bank_account_id: BANK_ACCOUNT_ID,
      }),
    ).toEqual([]);
  });

  it('rejects an amount of zero', () => {
    expect(
      issuePaths(QuickButtonSchema, {
        user_id: USER_ID,
        name: 'Nothing',
        mode: 'prompt',
        expense: 0,
      }),
    ).toEqual(['expense']);
  });

  it('rejects an empty label', () => {
    expect(issuePaths(QuickButtonSchema, { user_id: USER_ID, name: '', mode: 'prompt' })).toEqual([
      'name',
    ]);
  });
});
