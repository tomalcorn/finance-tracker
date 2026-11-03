import type { SubscriptionView, PaymentView } from '@/domain/readModels';

/** Where a subscription stands: still booking payments, turned off, or past its end date. */
export type SubscriptionStatus = 'active' | 'paused' | 'ended';

/** Where a subscription stands on `today`. Having ended outranks being turned off. */
export function statusOf(subscription: SubscriptionView, today: string): SubscriptionStatus {
  if (subscription.end_date !== null && subscription.end_date < today) return 'ended';
  return subscription.is_active ? 'active' : 'paused';
}

/** Whether a subscription is a joint contribution rather than an ordinary one. */
export function isContribution(subscription: SubscriptionView): boolean {
  return subscription.joint_income_source_id !== null;
}

/** The ones still booking payments, what costs most a month first, then by name. */
export function runningByCost(
  subscriptions: readonly SubscriptionView[],
  today: string,
): SubscriptionView[] {
  return subscriptions
    .filter((subscription) => statusOf(subscription, today) === 'active')
    .sort((a, b) => b.monthly_cost - a.monthly_cost || a.name.localeCompare(b.name));
}

/** The ones turned off or past their end date, by name. */
export function notRunning(
  subscriptions: readonly SubscriptionView[],
  today: string,
): SubscriptionView[] {
  return subscriptions
    .filter((subscription) => statusOf(subscription, today) !== 'active')
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** What the ones still booking payments cost a month, whatever their cadence. */
export function monthlyTotal(subscriptions: readonly SubscriptionView[], today: string): number {
  return subscriptions
    .filter((subscription) => statusOf(subscription, today) === 'active')
    .reduce((sum, subscription) => sum + subscription.monthly_cost, 0);
}

/** The date of a subscription's next booked payment, or undefined when none is booked. */
export function nextPaymentDate(
  payments: readonly PaymentView[],
  subscriptionId: string,
  today: string,
): string | undefined {
  return payments
    .filter(
      (payment) =>
        payment.subscription_id === subscriptionId &&
        payment.payment_type === 'expense' &&
        payment.payment_date >= today,
    )
    .map((payment) => payment.payment_date)
    .sort()[0];
}

/** How many payments are booked to a subscription, which go with it when it is deleted. */
export function bookedCount(payments: readonly PaymentView[], subscriptionId: string): number {
  return payments.filter((payment) => payment.subscription_id === subscriptionId).length;
}
