import type { BankAccountView, CategoryView, PaymentView } from '@/domain/readModels';
import {
  describeBudget,
  describeSpentChange,
  spentChange,
  summarise,
  type FinanceSummary,
} from '@/summary/financeSummary';

const NOW = '2026-11-15';
const ACCOUNT_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const ROOT_ID = '1a2b3c4d-0000-4000-8000-000000000001';

const OWNED = {
  user_id: 'auth0|test',
  name: 'Sample',
  _created_at: '2026-01-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
} as const;

function account(currentBalance: number): BankAccountView {
  return { ...OWNED, id: ACCOUNT_ID, starting_balance: 0, current_balance: currentBalance };
}

function category(overrides: Partial<CategoryView>): CategoryView {
  return {
    ...OWNED,
    id: ROOT_ID,
    parent_id: null,
    budget: 0,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: 0,
    progress: 0,
    split: 0,
    ...overrides,
  };
}

function expense(date: string, amount: number): PaymentView {
  return {
    ...OWNED,
    id: '4d5e6f70-0000-4000-8000-000000000001',
    payment_date: date,
    payment_type: 'expense',
    expense: amount,
    income: 0,
    checked: false,
    bank_account_id: ACCOUNT_ID,
    category_id: null,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

function income(date: string, amount: number): PaymentView {
  return { ...expense(date, 0), payment_type: 'income', income: amount };
}

function figures(overrides: Partial<FinanceSummary> = {}): FinanceSummary {
  return {
    totalBalance: 0,
    balanceHistory: [0, 0],
    totalBudget: 0,
    remainingBudget: 0,
    spent: 0,
    spentHistory: [0, 0],
    ...overrides,
  };
}

describe('summarise', () => {
  it('adds up every account', () => {
    const { totalBalance } = summarise([account(100), account(-30)], [], [], NOW);

    expect(totalBalance).toBe(70);
  });

  it('ends the balance history on the current balance', () => {
    const { balanceHistory } = summarise([account(100)], [], [expense(NOW, 30)], NOW);

    expect(balanceHistory.at(-1)).toBe(100);
  });

  it('covers six months of balances', () => {
    const { balanceHistory } = summarise([account(100)], [], [], NOW);

    expect(balanceHistory).toHaveLength(6);
  });

  it('undoes a month’s payments for the month before', () => {
    const { balanceHistory } = summarise(
      [account(100)],
      [],
      [expense('2026-11-02', 30), income('2026-11-03', 10)],
      NOW,
    );

    expect(balanceHistory.at(-2)).toBe(120);
  });

  it('leaves payments still to come out of the balance history', () => {
    const { balanceHistory } = summarise([account(100)], [], [expense('2026-11-20', 30)], NOW);

    expect(balanceHistory.at(-2)).toBe(100);
  });

  it('sums only the root budgets', () => {
    const { totalBudget } = summarise(
      [],
      [
        category({ budget: 1000 }),
        category({
          id: '1a2b3c4d-0000-4000-8000-000000000002',
          parent_id: ROOT_ID,
          budget: 400,
        }),
      ],
      [],
      NOW,
    );

    expect(totalBudget).toBe(1000);
  });

  it('sums only the root remainders', () => {
    const { remainingBudget } = summarise(
      [],
      [
        category({ remaining: 600 }),
        category({
          id: '1a2b3c4d-0000-4000-8000-000000000002',
          parent_id: ROOT_ID,
          remaining: 150,
        }),
      ],
      [],
      NOW,
    );

    expect(remainingBudget).toBe(600);
  });

  it('counts this month’s expenses as spent', () => {
    const { spent } = summarise(
      [],
      [],
      [expense('2026-11-02', 30), expense('2026-10-31', 500), income('2026-11-03', 900)],
      NOW,
    );

    expect(spent).toBe(30);
  });

  it('groups spending by month, oldest first', () => {
    const { spentHistory } = summarise(
      [],
      [],
      [expense('2026-11-02', 30), expense('2026-10-31', 500), expense('2026-06-01', 7)],
      NOW,
    );

    expect(spentHistory).toEqual([7, 0, 0, 0, 500, 30]);
  });

  it('leaves spending older than the history out', () => {
    const { spentHistory } = summarise([], [], [expense('2026-05-31', 500)], NOW);

    expect(spentHistory).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('crosses a new year', () => {
    const { spentHistory } = summarise([], [], [expense('2025-12-25', 40)], '2026-02-10');

    expect(spentHistory).toEqual([0, 0, 0, 40, 0, 0]);
  });
});

describe('describeBudget', () => {
  it('gives the share left of the total', () => {
    expect(describeBudget(figures({ totalBudget: 2000, remainingBudget: 800 }))).toBe(
      '40% of £2,000',
    );
  });

  it('says when no budget is set', () => {
    expect(describeBudget(figures())).toBe('no budget set');
  });
});

describe('spentChange', () => {
  it('is positive when more was spent than last month', () => {
    expect(spentChange(figures({ spentHistory: [10, 50, 80] }))).toBe(30);
  });
});

describe('describeSpentChange', () => {
  it('signs a rise', () => {
    expect(describeSpentChange(figures({ spentHistory: [50, 80] }))).toBe('+£30 vs last month');
  });

  it('signs a fall', () => {
    expect(describeSpentChange(figures({ spentHistory: [80, 50.5] }))).toBe(
      '-£29.50 vs last month',
    );
  });

  it('leaves the pence off a large change', () => {
    expect(describeSpentChange(figures({ spentHistory: [0, 1004.5] }))).toBe(
      '+£1,005 vs last month',
    );
  });

  it('says nothing when unchanged', () => {
    expect(describeSpentChange(figures({ spentHistory: [80, 80] }))).toBeNull();
  });
});
