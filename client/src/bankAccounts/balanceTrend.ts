import type { BankAccountView, PaymentView } from '@/domain/readModels';

/** How many months back an account's history reaches. */
export const TREND_MONTHS = 3;

/** Roughly how many days apart a sampled history's balances are. */
const SAMPLE_DAYS = 7;

const MS_PER_DAY = 86_400_000;

/** What an account held at the end of a day. */
export type BalancePoint = { date: string; balance: number };

function dayNumber(date: string): number {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

function dateOf(day: number): string {
  return new Date(day * MS_PER_DAY).toISOString().slice(0, 10);
}

function monthsBefore(date: string, months: number): string {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1 - months, day)).toISOString().slice(0, 10);
}

function toPence(amount: number): number {
  return Math.round(amount * 100) / 100;
}

/**
 * Work out an account's balance at the end of each day over the last `TREND_MONTHS`, oldest first.
 *
 * Starts the day before the window, or before the account began if that is later, so a payment on
 * the first day still shows as a move and there are never fewer than two points. Walks back from
 * `current_balance`, so the last point is always the balance shown beside it. Payments dated after
 * `now` are skipped, as `bank_accounts_view` skips them.
 *
 * @param now Today, as `YYYY-MM-DD`.
 */
export function dailyBalances(
  account: BankAccountView,
  payments: readonly PaymentView[],
  now: string,
): BalancePoint[] {
  const own = payments.filter(
    (payment) => payment.bank_account_id === account.id && payment.payment_date <= now,
  );
  const began = [
    account._created_at.slice(0, 10),
    ...own.map((payment) => payment.payment_date),
  ].reduce((earliest, date) => (date < earliest ? date : earliest), now);
  const windowStart = monthsBefore(now, TREND_MONTHS);
  const first = dayNumber(began > windowStart ? began : windowStart) - 1;
  const last = dayNumber(now);

  const moved = new Map<number, number>();
  for (const payment of own) {
    const day = dayNumber(payment.payment_date);
    moved.set(day, (moved.get(day) ?? 0) + payment.income - payment.expense);
  }

  const points: BalancePoint[] = [];
  let balance = account.current_balance;
  for (let day = last; day >= first; day -= 1) {
    points.unshift({ date: dateOf(day), balance: toPence(balance) });
    balance -= moved.get(day) ?? 0;
  }
  return points;
}

/** Thin a daily series to about one point per `SAMPLE_DAYS`, always keeping both ends. */
export function sampled<T>(daily: readonly T[]): T[] {
  const lastIndex = daily.length - 1;
  const steps = Math.max(Math.round(lastIndex / SAMPLE_DAYS), 1);
  const kept = new Set(
    Array.from({ length: steps + 1 }, (_, step) => Math.round((step * lastIndex) / steps)),
  );
  return daily.filter((_, index) => kept.has(index));
}
