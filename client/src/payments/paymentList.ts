import type { BankAccountView, PaymentView } from '@/domain/readModels';

/** Which payments a list shows: all of them, only money out, or only money in. */
export type PaymentKind = 'all' | 'expense' | 'income';

/** What narrows the list: a month as `YYYY-MM`, and a kind. */
export type PaymentFilter = { month: string; kind: PaymentKind };

/** One day of the list: its date, its payments newest first, and their net. */
export type PaymentDay = { date: string; payments: PaymentView[]; net: number };

/** A payment's amount as it moves the balance: money in positive, money out negative. */
export function signedAmount(payment: PaymentView): number {
  return payment.payment_type === 'income' ? payment.income : -payment.expense;
}

/**
 * Order payments newest first: by date, then the later-added first within a day, so a payment
 * just added tops its day. `_created_at` compares as text: every row carries the same UTC offset.
 */
export function newestFirst(a: PaymentView, b: PaymentView): number {
  if (a.payment_date !== b.payment_date) return a.payment_date < b.payment_date ? 1 : -1;
  if (a._created_at === b._created_at) return 0;
  return a._created_at < b._created_at ? 1 : -1;
}

/** The payments the filter lets through and `matches` accepts, newest first. */
export function filterPayments(
  payments: readonly PaymentView[],
  filter: PaymentFilter,
  matches: (payment: PaymentView) => boolean = () => true,
): PaymentView[] {
  return payments
    .filter((payment) => payment.payment_date.startsWith(`${filter.month}-`))
    .filter((payment) => filter.kind === 'all' || payment.payment_type === filter.kind)
    .filter(matches)
    .sort(newestFirst);
}

/** Group payments already newest first into days, keeping their order. */
export function byDay(payments: readonly PaymentView[]): PaymentDay[] {
  const days: PaymentDay[] = [];
  for (const payment of payments) {
    let day = days.at(-1);
    if (day?.date !== payment.payment_date) {
      day = { date: payment.payment_date, payments: [], net: 0 };
      days.push(day);
    }
    day.payments.push(payment);
    day.net += signedAmount(payment);
  }
  return days;
}

/** One category's spending: its id (null for none), its expenses in order, and their total. */
export type CategorySpend = { categoryId: string | null; payments: PaymentView[]; total: number };

/**
 * The expenses among some payments, grouped by category, the most spent first, each group keeping
 * the payments' order. Income is left out.
 */
export function byCategory(payments: readonly PaymentView[]): CategorySpend[] {
  const groups = new Map<string | null, CategorySpend>();
  for (const payment of payments) {
    if (payment.payment_type !== 'expense') continue;
    const group = groups.get(payment.category_id) ?? {
      categoryId: payment.category_id,
      payments: [],
      total: 0,
    };
    group.payments.push(payment);
    group.total += payment.expense;
    groups.set(payment.category_id, group);
  }
  return [...groups.values()].sort((a, b) => b.total - a.total);
}

/** What went out and came in across some payments, each as a positive amount. */
export function totals(payments: readonly PaymentView[]): { out: number; in: number } {
  return payments.reduce(
    (sum, payment) =>
      payment.payment_type === 'income'
        ? { ...sum, in: sum.in + payment.income }
        : { ...sum, out: sum.out + payment.expense },
    { out: 0, in: 0 },
  );
}

/** One account's balance at the end of a day. */
export type ClosingBalance = { name: string; balance: number };

/**
 * The end-of-day balance of each account with a payment in `day`, in name order: its starting
 * balance plus the net of every payment up to and including that day.
 *
 * Args:
 *   day: The day as listed, so only the accounts it shows are included.
 *   payments: Every payment, not just those listed, so a filter can't change a balance.
 */
export function closingBalances(
  day: PaymentDay,
  accounts: readonly BankAccountView[],
  payments: readonly PaymentView[],
): ClosingBalance[] {
  const moved = new Set(day.payments.map((payment) => payment.bank_account_id));
  return accounts
    .filter((account) => moved.has(account.id))
    .map((account) => ({
      name: account.name,
      balance: payments
        .filter(
          (payment) => payment.bank_account_id === account.id && payment.payment_date <= day.date,
        )
        .reduce((sum, payment) => sum + signedAmount(payment), account.starting_balance),
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * How many days up to `today` have payments but none ticked. Ticking one payment checks off its
 * day, and a day still to come can't be checked yet.
 */
export function uncheckedDays(payments: readonly PaymentView[], today: string): number {
  const due = payments.filter((payment) => payment.payment_date <= today);
  const days = new Set(due.map((payment) => payment.payment_date));
  for (const payment of due) {
    if (payment.checked) days.delete(payment.payment_date);
  }
  return days.size;
}

/** The month of a `YYYY-MM-DD` date, as `YYYY-MM`. */
export function monthOf(date: string): string {
  return date.slice(0, 7);
}

/** The month `count` months after a `YYYY-MM` month (before, when negative). */
export function shiftMonth(month: string, count: number): string {
  const [year = 0, number = 1] = month.split('-').map(Number);
  const index = year * 12 + (number - 1) + count;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;
}
