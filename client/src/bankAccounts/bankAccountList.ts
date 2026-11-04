import type { BankAccountView, PaymentView, SubscriptionView } from '@/domain/readModels';

/** The accounts in name order. */
export function byName(accounts: readonly BankAccountView[]): BankAccountView[] {
  return [...accounts].sort((a, b) => a.name.localeCompare(b.name));
}

/** What the accounts hold between them, with any overdrawn account counting against the rest. */
export function totalBalance(accounts: readonly BankAccountView[]): number {
  return accounts.reduce((total, account) => total + account.current_balance, 0);
}

/**
 * Whether a payment or subscription uses an account, in any month: the database won't delete one
 * that is. A joint contribution uses both the account it leaves and the one it arrives in.
 */
export function isInUse(
  accountId: string,
  payments: readonly PaymentView[],
  subscriptions: readonly SubscriptionView[],
): boolean {
  return (
    payments.some((payment) => payment.bank_account_id === accountId) ||
    subscriptions.some(
      (subscription) =>
        subscription.bank_account_id === accountId ||
        subscription.joint_bank_account_id === accountId,
    )
  );
}
