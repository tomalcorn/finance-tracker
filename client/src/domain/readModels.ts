// Read models: the rows the app reads, carrying each SQL view's computed columns
// (`src/domain/read_models.py`). Every column is required unless the database
// allows null, so a column missing from a view fails the read instead of
// defaulting.
import { z } from 'zod';

import {
  AccrualPeriodSchema,
  CadenceSchema,
  IncomeRollUpPeriodSchema,
  OwnershipTypeSchema,
  QuickButtonModeSchema,
  requireJointAccount,
} from '@/domain/entities';

const viewFields = {
  id: z.uuid(),
  user_id: z.string(),
  name: z.string(),
  _created_at: z.iso.datetime({ offset: true }),
  ownership_type: OwnershipTypeSchema,
  joint_account_id: z.uuid().nullable(),
};

/** A row of `bank_accounts_view`. */
export const BankAccountViewSchema = z
  .object({
    ...viewFields,
    starting_balance: z.number(),
    /** `starting_balance` plus the net of every payment. */
    current_balance: z.number(),
  })
  .superRefine(requireJointAccount);
export type BankAccountView = z.infer<typeof BankAccountViewSchema>;

/** A row of `categories_view`, a root or a subcategory alike. */
export const CategoryViewSchema = z
  .object({
    ...viewFields,
    parent_id: z.uuid().nullable(),
    budget: z.number().nonnegative(),
    accrual: AccrualPeriodSchema,
    cost: z.number().nonnegative(),
    starting_balance: z.number(),
    /**
     * Payments over the row's window: this month's (its own plus its children's)
     * for a monthly category, or a pot's starting balance plus everything since
     * it opened. Negative when refunds outweigh spending.
     */
    accrued: z.number(),
    /** Budget minus accrued, or a pot's cost minus what it holds. Negative once overspent. */
    remaining: z.number(),
    /** Percentage of budget used. Unbounded: above 100 when overspent, below 0 after refunds. */
    progress: z.number(),
    /**
     * The budget as a percentage of what it is measured against: total income
     * for a root, the parent's budget for a monthly child, and what the parent
     * has left to allocate for a pot. Can exceed 100.
     */
    split: z.number().nonnegative(),
  })
  .superRefine(requireJointAccount);
export type CategoryView = z.infer<typeof CategoryViewSchema>;

/** A row of `income_sources_view`. */
export const IncomeSourceViewSchema = z
  .object({
    ...viewFields,
    budget_tracker_ids: z.array(z.uuid()),
    /** Income payments over the month `income_roll_up_period` selects. */
    current_month: z.number(),
    income_roll_up_period: IncomeRollUpPeriodSchema,
  })
  .superRefine(requireJointAccount);
export type IncomeSourceView = z.infer<typeof IncomeSourceViewSchema>;

/** A row of `subscriptions_view`. */
export const SubscriptionViewSchema = z
  .object({
    ...viewFields,
    amount: z.number(),
    cadence: CadenceSchema,
    bank_account_id: z.uuid(),
    category_id: z.uuid().nullable(),
    start_date: z.iso.date(),
    end_date: z.iso.date().nullable(),
    is_active: z.boolean(),
    /** `amount` as a monthly equivalent. */
    monthly_cost: z.number(),
    joint_income_source_id: z.uuid().nullable(),
    joint_bank_account_id: z.uuid().nullable(),
  })
  .superRefine(requireJointAccount);
export type SubscriptionView = z.infer<typeof SubscriptionViewSchema>;

/**
 * A row of the `payments` table, which has no view: the flat union of expense
 * and income columns, with the source column of the other kind null.
 */
export const PaymentViewSchema = z
  .object({
    ...viewFields,
    payment_date: z.iso.date(),
    payment_type: z.enum(['expense', 'income']),
    expense: z.number(),
    income: z.number(),
    checked: z.boolean(),
    bank_account_id: z.uuid(),
    category_id: z.uuid().nullable(),
    income_source_id: z.uuid().nullable(),
    subscription_id: z.uuid().nullable(),
    linked_payment_id: z.uuid().nullable(),
  })
  .superRefine(requireJointAccount);
export type PaymentView = z.infer<typeof PaymentViewSchema>;

/** A row of the `quick_buttons` table, which has no view. */
export const QuickButtonViewSchema = z
  .object({
    ...viewFields,
    mode: QuickButtonModeSchema,
    payment_name: z.string().nullable(),
    expense: z.number().nullable(),
    bank_account_id: z.uuid().nullable(),
    category_id: z.uuid().nullable(),
    icon: z.string().nullable(),
    display_order: z.int(),
  })
  .superRefine(requireJointAccount);
export type QuickButtonView = z.infer<typeof QuickButtonViewSchema>;

/** A row of the `user_settings` table, which has no view. */
export const UserSettingsViewSchema = z
  .object({ ...viewFields, income_roll_up_period: IncomeRollUpPeriodSchema })
  .superRefine(requireJointAccount);
export type UserSettingsView = z.infer<typeof UserSettingsViewSchema>;

/** A row of the `joint_accounts` table. */
export const JointAccountViewSchema = z.object({ id: z.uuid(), name: z.string() });
export type JointAccountView = z.infer<typeof JointAccountViewSchema>;

/** A row of the `joint_account_members` table. */
export const JointAccountMemberViewSchema = z.object({
  id: z.uuid(),
  joint_account_id: z.uuid(),
  user_id: z.string(),
});
export type JointAccountMemberView = z.infer<typeof JointAccountMemberViewSchema>;
