import type { BankAccountView, PaymentView } from '@/domain/readModels';
import { formatAmountCompact } from '@/theme/formatAmount';
import { formatDayOfMonth } from '@/theme/formatDate';

/** How many months back an account's trend reaches. */
export const TREND_MONTHS = 3;

/** Roughly how many days apart a trend's balances are. */
const SAMPLE_DAYS = 7;

/** The size of change from which pence are left off, to keep it on one line of a narrow tile. */
const PENCE_BELOW = 100;

const MS_PER_DAY = 86_400_000;

/** How an account's balance has moved up to today. */
export type BalanceTrend = {
  /** The first day covered: the window's start, or the day the account began if that is later. */
  from: string;
  /** Whether the account is too young to fill the window. */
  partial: boolean;
  /**
   * The balance going into `from`, then about every `SAMPLE_DAYS` up to today's. Never fewer than
   * two, and evenly enough spaced to draw as if they were even.
   */
  balances: number[];
  /** What today's balance is up or down on the first of `balances`, to the penny. */
  change: number;
};

function dayNumber(date: string): number {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

function monthsBefore(date: string, months: number): string {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1 - months, day)).toISOString().slice(0, 10);
}

/** Thin a daily series to about one value per `SAMPLE_DAYS`, always keeping both ends. */
function sampled(daily: readonly number[]): number[] {
  const lastIndex = daily.length - 1;
  const steps = Math.max(Math.round(lastIndex / SAMPLE_DAYS), 1);
  const kept = new Set(
    Array.from({ length: steps + 1 }, (_, step) => Math.round((step * lastIndex) / steps)),
  );
  return daily.filter((_, index) => kept.has(index));
}

function toPence(amount: number): number {
  return Math.round(amount * 100) / 100;
}

/**
 * Work out how an account's balance has moved over the last `TREND_MONTHS`.
 *
 * Walks back from `current_balance`, so the trend always ends on the balance shown beside it.
 * Payments dated after `now` are skipped, as `bank_accounts_view` skips them.
 *
 * @param now Today, as `YYYY-MM-DD`.
 */
export function balanceTrend(
  account: BankAccountView,
  payments: readonly PaymentView[],
  now: string,
): BalanceTrend {
  const own = payments.filter(
    (payment) => payment.bank_account_id === account.id && payment.payment_date <= now,
  );
  const began = [
    account._created_at.slice(0, 10),
    ...own.map((payment) => payment.payment_date),
  ].reduce((earliest, date) => (date < earliest ? date : earliest), now);
  const windowStart = monthsBefore(now, TREND_MONTHS);
  const partial = began > windowStart;
  const from = partial ? began : windowStart;

  const first = dayNumber(from);
  const moved = new Map<number, number>();
  for (const payment of own) {
    const index = dayNumber(payment.payment_date) - first;
    moved.set(index, (moved.get(index) ?? 0) + payment.income - payment.expense);
  }

  const days = dayNumber(now) - first + 1;
  const balances = new Array<number>(days + 1);
  let balance = account.current_balance;
  for (let index = days - 1; index >= 0; index -= 1) {
    balances[index + 1] = toPence(balance);
    balance -= moved.get(index) ?? 0;
  }
  balances[0] = toPence(balance);

  return {
    from,
    partial,
    balances: sampled(balances),
    change: toPence(account.current_balance - balance),
  };
}

/** Say how far a trend moved and over what span, e.g. `+£250 in 3 months` or `-£3.40 since 12 Oct`. */
export function describeChange({ change, from, partial }: BalanceTrend): string {
  const span = partial ? `since ${formatDayOfMonth(from)}` : `in ${TREND_MONTHS} months`;
  if (change === 0) return `Flat ${span}`;
  const amount = Math.abs(change) < PENCE_BELOW ? change : Math.round(change);
  return `${change > 0 ? '+' : ''}${formatAmountCompact(amount)} ${span}`;
}
