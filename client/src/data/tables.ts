/** A writable table. */
export type TableName =
  | 'bank_accounts'
  | 'categories'
  | 'income_sources'
  | 'joint_account_members'
  | 'joint_accounts'
  | 'payments'
  | 'quick_buttons'
  | 'subscriptions'
  | 'user_settings';

/** A read-only view computing columns over a table. */
export type ViewName =
  'bank_accounts_view' | 'categories_view' | 'income_sources_view' | 'subscriptions_view';

/** Where a repository reads from: a view, or the table itself when it has none. */
export type ReadSource = TableName | ViewName;

/** The views that sum payments, so any write to payments restates them. */
const PAYMENT_DERIVED: readonly ReadSource[] = [
  'bank_accounts_view',
  'categories_view',
  'income_sources_view',
];

/**
 * What else a write to each table changes, beyond the table itself: the views
 * computed from it, and the tables an `ON DELETE CASCADE` writes on its behalf.
 * All within the written row's own ownership.
 */
export const AFFECTED_BY: Readonly<Partial<Record<TableName, readonly ReadSource[]>>> = {
  payments: PAYMENT_DERIVED,
  bank_accounts: ['bank_accounts_view'],
  // A root's `split` divides by total income.
  income_sources: ['income_sources_view', 'categories_view'],
  // Deleting a subscription cascades to the payments it generated.
  subscriptions: ['subscriptions_view', 'payments', ...PAYMENT_DERIVED],
  // A child rolls up into its parent, and deleting one repoints what referenced it.
  categories: ['categories_view', 'payments', 'subscriptions_view', 'quick_buttons'],
  // The roll-up period decides which month income sources total.
  user_settings: ['income_sources_view', 'categories_view'],
};

/**
 * Cascades that cross from a personal write into joint rows. A joint
 * contribution's income leg is joint-owned but carries the personal
 * subscription's id, so deleting the subscription deletes joint payments.
 */
export const CASCADES_TO_JOINT: Readonly<Partial<Record<TableName, readonly ReadSource[]>>> = {
  subscriptions: ['payments', ...PAYMENT_DERIVED],
};
