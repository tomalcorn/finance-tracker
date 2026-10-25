// Write models: the rows the app writes, one schema per aggregate (`src/domain/entities.py`).
import { z } from 'zod';

/** An unvalidated field map on its way into an entity. */
export type RawRow = Readonly<Record<string, unknown>>;

export const OwnershipTypeSchema = z.enum(['personal', 'joint']);
export type OwnershipType = z.infer<typeof OwnershipTypeSchema>;

export const AccrualPeriodSchema = z.enum(['monthly', 'multi_month']);
export type AccrualPeriod = z.infer<typeof AccrualPeriodSchema>;

export const CadenceSchema = z.enum(['weekly', 'monthly', 'quarterly', 'biannually', 'yearly']);
export type Cadence = z.infer<typeof CadenceSchema>;

export const QuickButtonModeSchema = z.enum(['log', 'prompt']);
export type QuickButtonMode = z.infer<typeof QuickButtonModeSchema>;

export const IncomeRollUpPeriodSchema = z.enum(['current_month', 'previous_month']);
export type IncomeRollUpPeriod = z.infer<typeof IncomeRollUpPeriodSchema>;

/** A new row id. */
export function newId(): string {
  return crypto.randomUUID();
}

/** Today's local date as `YYYY-MM-DD`, the form date columns take. */
export function today(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Whether a row names its joint account, as every joint-owned row must. */
export function hasJointAccount(row: {
  ownership_type: OwnershipType;
  joint_account_id: string | null;
}): boolean {
  return row.ownership_type !== 'joint' || row.joint_account_id !== null;
}

/** The issue `hasJointAccount` reports. */
export const NEEDS_JOINT_ACCOUNT = {
  path: ['joint_account_id'],
  message: 'A joint-owned row needs a joint account.',
};

const entityFields = {
  id: z.uuid().default(newId),
  user_id: z.string(),
  name: z.string().default(''),
  ownership_type: OwnershipTypeSchema.default('personal'),
  joint_account_id: z.uuid().nullable().default(null),
};

export const BankAccountSchema = z
  .object({ ...entityFields, starting_balance: z.number().default(0) })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT);
export type BankAccount = z.infer<typeof BankAccountSchema>;

/**
 * A category money can be attributed to: a root (`parent_id` null) or a
 * subcategory under one. A `multi_month` subcategory is a pot, filling towards
 * `cost` over several months instead of resetting.
 */
export const CategorySchema = z
  .object({
    ...entityFields,
    parent_id: z.uuid().nullable().default(null),
    budget: z.number().nonnegative().default(0),
    accrual: AccrualPeriodSchema.default('monthly'),
    cost: z.number().nonnegative().default(0),
    starting_balance: z.number().default(0),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT)
  .refine((category) => category.parent_id !== category.id, {
    path: ['parent_id'],
    message: 'A category cannot be its own parent.',
  })
  .refine((category) => category.accrual !== 'multi_month' || category.parent_id !== null, {
    path: ['accrual'],
    message: 'Only a subcategory can accrue across months.',
  });
export type Category = z.infer<typeof CategorySchema>;

export const IncomeSourceSchema = z
  .object({ ...entityFields, budget_tracker_ids: z.array(z.uuid()).default([]) })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT);
export type IncomeSource = z.infer<typeof IncomeSourceSchema>;

/**
 * A recurring payment. One with `joint_income_source_id` set is a joint
 * contribution, booking a matching joint income each cadence; it needs
 * `joint_bank_account_id` too, and only a personal subscription can be one.
 */
export const SubscriptionSchema = z
  .object({
    ...entityFields,
    amount: z.number().default(0),
    cadence: CadenceSchema.default('monthly'),
    bank_account_id: z.uuid(),
    category_id: z.uuid().nullable().default(null),
    start_date: z.iso.date().default(today),
    end_date: z.iso.date().nullable().default(null),
    is_active: z.boolean().default(true),
    joint_income_source_id: z.uuid().nullable().default(null),
    joint_bank_account_id: z.uuid().nullable().default(null),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT)
  .refine(
    (subscription) =>
      subscription.joint_income_source_id !== null || subscription.joint_bank_account_id === null,
    {
      path: ['joint_income_source_id'],
      message: 'A joint contribution needs both joint fields.',
    },
  )
  .refine(
    (subscription) =>
      subscription.joint_bank_account_id !== null || subscription.joint_income_source_id === null,
    {
      path: ['joint_bank_account_id'],
      message: 'A joint contribution needs both joint fields.',
    },
  )
  .refine(
    (subscription) =>
      subscription.joint_income_source_id === null || subscription.ownership_type === 'personal',
    {
      path: ['joint_income_source_id'],
      message: 'Only a personal subscription can be a joint contribution.',
    },
  );
export type Subscription = z.infer<typeof SubscriptionSchema>;

const paymentFields = {
  ...entityFields,
  payment_date: z.iso.date().default(today),
  checked: z.boolean().default(false),
  bank_account_id: z.uuid(),
  subscription_id: z.uuid().nullable().default(null),
  linked_payment_id: z.uuid().nullable().default(null),
};

export const ExpensePaymentSchema = z
  .object({
    ...paymentFields,
    payment_type: z.literal('expense'),
    expense: z.number().default(0),
    income: z.number().default(0),
    category_id: z.uuid().nullable().default(null),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT);
export type ExpensePayment = z.infer<typeof ExpensePaymentSchema>;

export const IncomePaymentSchema = z
  .object({
    ...paymentFields,
    payment_type: z.literal('income'),
    income: z.number().default(0),
    expense: z.number().default(0),
    income_source_id: z.uuid().nullable().default(null),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT);
export type IncomePayment = z.infer<typeof IncomePaymentSchema>;

/** A payment, told apart by `payment_type`. */
export const PaymentSchema = z.discriminatedUnion('payment_type', [
  ExpensePaymentSchema,
  IncomePaymentSchema,
]);
export type Payment = z.infer<typeof PaymentSchema>;

/**
 * A preset expense behind a quick-entry button. `name` labels the button; the
 * payment fields are the preset. A `log` button writes its payment on tap, so it
 * needs `expense` and `bank_account_id`; a `prompt` button opens a form instead.
 * The amount may be negative (money coming back) but never zero.
 */
export const QuickButtonSchema = z
  .object({
    ...entityFields,
    name: z.string().min(1),
    payment_name: z.string().nullable().default(null),
    mode: QuickButtonModeSchema.default('log'),
    expense: z.number().nullable().default(null),
    bank_account_id: z.uuid().nullable().default(null),
    category_id: z.uuid().nullable().default(null),
    icon: z.string().nullable().default(null),
    display_order: z.int().nonnegative().default(0),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT)
  .refine((button) => button.mode !== 'log' || button.expense !== null, {
    path: ['expense'],
    message: 'A log button needs an amount to write a payment.',
  })
  .refine((button) => button.mode !== 'log' || button.bank_account_id !== null, {
    path: ['bank_account_id'],
    message: 'A log button needs a bank account to write a payment.',
  })
  .refine((button) => button.expense !== 0, {
    path: ['expense'],
    message: 'A quick button cannot preset an amount of zero.',
  });
export type QuickButton = z.infer<typeof QuickButtonSchema>;

/** The preferences for one half of a user's finances: personal, or their joint account's. */
export const UserSettingsSchema = z
  .object({
    ...entityFields,
    income_roll_up_period: IncomeRollUpPeriodSchema.default('current_month'),
  })
  .refine(hasJointAccount, NEEDS_JOINT_ACCOUNT);
export type UserSettings = z.infer<typeof UserSettingsSchema>;

/** A shared account. It has no single owner, so no `user_id` or ownership columns. */
export const JointAccountSchema = z.object({
  id: z.uuid().default(newId),
  name: z.string().min(1),
});
export type JointAccount = z.infer<typeof JointAccountSchema>;

export const JointAccountMemberSchema = z.object({
  id: z.uuid().default(newId),
  joint_account_id: z.uuid(),
  user_id: z.string(),
});
export type JointAccountMember = z.infer<typeof JointAccountMemberSchema>;
