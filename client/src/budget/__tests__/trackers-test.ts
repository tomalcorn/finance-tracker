import {
  childrenOf,
  paymentsCountedIn,
  plansFit,
  potPlan,
  roots,
  takesSubcategories,
  totalAllocated,
  totalIncome,
} from '@/budget/trackers';
import type { CategoryView, IncomeSourceView, PaymentView } from '@/domain/readModels';

function category(id: string, name: string, parentId: string | null = null): CategoryView {
  return {
    id,
    user_id: 'auth0|test',
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: parentId,
    budget: 100,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: 100,
    progress: 0,
    split: 0,
  };
}

describe('roots', () => {
  it('orders the seeded trackers as the app always shows them, then any other by name', () => {
    const categories = [
      category('1', 'Savings'),
      category('2', 'Holidays'),
      category('3', 'Expenses'),
      category('4', 'One-offs'),
      category('5', 'Joint'),
      category('6', 'Groceries', '3'),
    ];

    expect(roots(categories).map((root) => root.name)).toEqual([
      'Expenses',
      'Joint',
      'One-offs',
      'Savings',
      'Holidays',
    ]);
  });
});

describe('childrenOf', () => {
  it('lists one tracker’s subcategories by name', () => {
    const categories = [
      category('1', 'Expenses'),
      category('2', 'Transport', '1'),
      category('3', 'Groceries', '1'),
      category('4', 'Bike', '9'),
    ];

    expect(childrenOf(categories, '1').map((child) => child.name)).toEqual([
      'Groceries',
      'Transport',
    ]);
  });
});

describe('takesSubcategories', () => {
  it.each([
    ['Expenses', true],
    ['One-offs', true],
    ['Joint', false],
    ['Savings', false],
  ])('%s takes subcategories: %p', (name, expected) => {
    expect(takesSubcategories(category('1', name))).toBe(expected);
  });
});

describe('totals', () => {
  it('adds up the income sources for the roll-up month', () => {
    const sources = [{ current_month: 2000 }, { current_month: 450.5 }] as IncomeSourceView[];

    expect(totalIncome(sources)).toBe(2450.5);
  });

  it('adds up the trackers’ budgets', () => {
    expect(totalAllocated([category('1', 'Expenses'), category('2', 'Savings')])).toBe(200);
  });
});

describe('paymentsCountedIn', () => {
  const groceries = category('1', 'Groceries', '9');
  const bike = { ...category('2', 'Bike', '8'), accrual: 'multi_month' as const };

  function payment(id: string, categoryId: string, date: string): PaymentView {
    return {
      id,
      user_id: 'auth0|test',
      name: id,
      _created_at: '2026-10-01T09:30:12.345678+00:00',
      ownership_type: 'personal',
      joint_account_id: null,
      payment_date: date,
      payment_type: 'expense',
      expense: 10,
      income: 0,
      checked: false,
      bank_account_id: 'b',
      category_id: categoryId,
      income_source_id: null,
      subscription_id: null,
      linked_payment_id: null,
    };
  }

  const payments = [
    payment('old', '1', '2026-10-31'),
    payment('first', '1', '2026-11-01'),
    payment('latest', '1', '2026-11-20'),
    payment('other', '3', '2026-11-05'),
    payment('banked', '2', '2026-03-01'),
  ];

  it('counts a monthly subcategory’s payments this month, newest first', () => {
    expect(paymentsCountedIn(payments, groceries, '2026-11-25').map((p) => p.id)).toEqual([
      'latest',
      'first',
    ]);
  });

  it('counts everything paid into a pot', () => {
    expect(paymentsCountedIn(payments, bike, '2026-11-25').map((p) => p.id)).toEqual(['banked']);
  });
});

describe('potPlan', () => {
  function pot(saved: number, cost: number, planned: number): CategoryView {
    return {
      ...category('1', 'Bike', '9'),
      accrual: 'multi_month',
      budget: planned,
      cost,
      accrued: saved,
      remaining: cost - saved,
      progress: (saved / cost) * 100,
    };
  }

  it('says what is left to go once the plan is banked', () => {
    expect(potPlan(pot(300, 800, 150))).toMatchObject({
      after: 350,
      plannedProgress: 18.75,
      summary: '£350.00 to go after this month',
    });
  });

  it('says when the plan reaches the goal', () => {
    expect(potPlan(pot(700, 800, 100))?.summary).toBe('Goal reached this month');
  });

  it('says how much more than needed the plan is, and stops the bar at the goal', () => {
    expect(potPlan(pot(700, 800, 130))).toMatchObject({
      after: -30,
      plannedProgress: 12.5,
      summary: 'Goal reached this month, £30.00 more than needed',
    });
  });

  it('has nothing to show with nothing planned, or once the pot is saved', () => {
    expect(potPlan(pot(300, 800, 0))).toBeNull();
    expect(potPlan(pot(800, 800, 50))).toBeNull();
  });

  it('previews an amount in place of the pot’s own plan', () => {
    expect(potPlan(pot(300, 800, 150), 200.1)?.after).toBe(299.9);
    expect(potPlan(pot(300, 800, 150), 0)).toBeNull();
  });
});

describe('plansFit', () => {
  const tracker = { ...category('9', 'One-offs'), budget: 200 };
  const pot = (planned: number) => ({ ...category(String(planned), 'Pot', '9'), budget: planned });

  it('says how much of the budget the plans leave', () => {
    expect(plansFit(tracker, [pot(100), pot(50)]).summary).toBe(
      '£150.00 planned across pots · £50.00 of the budget unplanned',
    );
  });

  it('says when the plans use all of the budget', () => {
    expect(plansFit(tracker, [pot(120), pot(80)]).summary).toBe(
      '£200.00 planned across pots · all of the budget',
    );
  });

  it('says when the plans are more than the budget', () => {
    expect(plansFit(tracker, [pot(180), pot(50)])).toMatchObject({
      left: -30,
      summary: '£230.00 planned across pots · £30.00 more than the budget',
    });
  });
});
