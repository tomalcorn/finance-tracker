import { roots } from '@/budget/trackers';
import type { BankAccountView, CategoryView, PaymentView } from '@/domain/readModels';
import { monthOf, shiftMonth } from '@/payments/paymentList';
import { formatAmountCompact } from '@/theme/formatAmount';

/** How many months each history covers, the current one included. */
export const HISTORY_MONTHS = 6;

/** The size of change from which pence are left off, to keep it on one line of a narrow tile. */
const PENCE_BELOW = 100;

/** The headline figures for one half. Each history runs oldest first and ends on this month. */
export type FinanceSummary = {
  /** What every account holds now. */
  totalBalance: number;
  /** What every account held between them at each month's end, this month's being now. */
  balanceHistory: number[];
  /** The root categories' budgets added up: a child's budget is already part of its root's. */
  totalBudget: number;
  /** What is left of those budgets this month. */
  remainingBudget: number;
  /** Expenses dated this month. */
  spent: number;
  /** Expenses dated in each month. */
  spentHistory: number[];
};

function toPence(amount: number): number {
  return Math.round(amount * 100) / 100 + 0;
}

/**
 * Fold one half's rows into its headline figures.
 *
 * Earlier balances are found by undoing each month's payments from the current one. Payments still
 * to come are skipped there, because `bank_accounts_view` leaves them out of the current balance.
 *
 * @param now Today, as `YYYY-MM-DD`.
 */
export function summarise(
  accounts: readonly BankAccountView[],
  categories: readonly CategoryView[],
  payments: readonly PaymentView[],
  now: string,
): FinanceSummary {
  const thisMonth = monthOf(now);
  const months = Array.from({ length: HISTORY_MONTHS }, (_, index) =>
    shiftMonth(thisMonth, index - HISTORY_MONTHS + 1),
  );

  const expenses = new Map<string, number>();
  const nets = new Map<string, number>();
  for (const payment of payments) {
    const month = monthOf(payment.payment_date);
    expenses.set(month, (expenses.get(month) ?? 0) + payment.expense);
    if (payment.payment_date <= now) {
      nets.set(month, (nets.get(month) ?? 0) + payment.income - payment.expense);
    }
  }

  const totalBalance = toPence(accounts.reduce((sum, account) => sum + account.current_balance, 0));
  const balanceHistory: number[] = [];
  let balance = totalBalance;
  for (const month of [...months].reverse()) {
    balanceHistory.unshift(toPence(balance));
    balance -= nets.get(month) ?? 0;
  }

  const trackers = roots(categories);
  return {
    totalBalance,
    balanceHistory,
    totalBudget: toPence(trackers.reduce((sum, tracker) => sum + tracker.budget, 0)),
    remainingBudget: toPence(trackers.reduce((sum, tracker) => sum + tracker.remaining, 0)),
    spent: toPence(expenses.get(thisMonth) ?? 0),
    spentHistory: months.map((month) => toPence(expenses.get(month) ?? 0)),
  };
}

/** Say how much of the budget is left, e.g. `40% of £2,000`. */
export function describeBudget({ totalBudget, remainingBudget }: FinanceSummary): string {
  if (totalBudget <= 0) return 'no budget set';
  const share = Math.round((remainingBudget / totalBudget) * 100);
  return `${share}% of ${formatAmountCompact(totalBudget)}`;
}

/** How much more was spent this month than last, or a negative amount for less. */
export function spentChange({ spentHistory }: FinanceSummary): number {
  const [last = 0, current = 0] = spentHistory.slice(-2);
  return toPence(current - last);
}

/** Say how this month's spending compares with last month's, or nothing if they are the same. */
export function describeSpentChange(summary: FinanceSummary): string | null {
  const change = spentChange(summary);
  if (change === 0) return null;
  const amount = Math.abs(change) < PENCE_BELOW ? change : Math.round(change);
  return `${change > 0 ? '+' : ''}${formatAmountCompact(amount)} vs last month`;
}
