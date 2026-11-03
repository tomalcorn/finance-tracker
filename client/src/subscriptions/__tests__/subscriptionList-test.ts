import type { PaymentView, SubscriptionView } from '@/domain/readModels';
import {
  bookedCount,
  isContribution,
  monthlyTotal,
  nextPaymentDate,
  notRunning,
  runningByCost,
  statusOf,
} from '@/subscriptions/subscriptionList';

const TODAY = '2026-11-15';

function subscription(name: string, overrides: Partial<SubscriptionView> = {}): SubscriptionView {
  return {
    id: name,
    user_id: 'auth0|test',
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    amount: 10,
    cadence: 'monthly',
    bank_account_id: 'b',
    category_id: null,
    start_date: '2026-01-01',
    end_date: null,
    is_active: true,
    monthly_cost: 10,
    joint_income_source_id: null,
    joint_bank_account_id: null,
    ...overrides,
  };
}

function payment(subscriptionId: string | null, date: string): PaymentView {
  return {
    id: `${subscriptionId}-${date}`,
    user_id: 'auth0|test',
    name: 'Sub',
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    payment_date: date,
    payment_type: 'expense',
    expense: 10,
    income: 0,
    checked: false,
    bank_account_id: 'b',
    category_id: null,
    income_source_id: null,
    subscription_id: subscriptionId,
    linked_payment_id: null,
  };
}

const PAUSED = subscription('Paused', { is_active: false });
const ENDED = subscription('Ended', { end_date: '2026-11-14' });
const RUNNING = subscription('Running');

describe('statusOf', () => {
  it('is active while it is on', () => {
    expect(statusOf(RUNNING, TODAY)).toBe('active');
  });

  it('is paused once turned off', () => {
    expect(statusOf(PAUSED, TODAY)).toBe('paused');
  });

  it('is ended once past its end date', () => {
    expect(statusOf(ENDED, TODAY)).toBe('ended');
  });

  it('is still active on its last day', () => {
    expect(statusOf(subscription('Last', { end_date: TODAY }), TODAY)).toBe('active');
  });

  it('counts as ended even when also turned off', () => {
    expect(statusOf({ ...ENDED, is_active: false }, TODAY)).toBe('ended');
  });
});

describe('isContribution', () => {
  it('is true with a joint income source', () => {
    expect(isContribution(subscription('C', { joint_income_source_id: 's' }))).toBe(true);
  });

  it('is false without one', () => {
    expect(isContribution(RUNNING)).toBe(false);
  });
});

describe('runningByCost', () => {
  it('puts what costs most a month first', () => {
    const big = subscription('Big', { monthly_cost: 50 });
    const small = subscription('Small', { monthly_cost: 1 });

    expect(runningByCost([small, big, RUNNING], TODAY).map((row) => row.name)).toEqual([
      'Big',
      'Running',
      'Small',
    ]);
  });

  it('breaks a tie by name', () => {
    const zebra = subscription('Zebra');
    const apple = subscription('Apple');

    expect(runningByCost([zebra, apple], TODAY).map((row) => row.name)).toEqual(['Apple', 'Zebra']);
  });

  it('leaves out what isn’t running', () => {
    expect(runningByCost([PAUSED, ENDED], TODAY)).toEqual([]);
  });
});

describe('notRunning', () => {
  it('holds what is turned off or ended, by name', () => {
    expect(notRunning([RUNNING, PAUSED, ENDED], TODAY).map((row) => row.name)).toEqual([
      'Ended',
      'Paused',
    ]);
  });
});

describe('monthlyTotal', () => {
  it('adds up only the running ones', () => {
    const yearly = subscription('Yearly', { amount: 120, monthly_cost: 10 });

    expect(monthlyTotal([RUNNING, yearly, PAUSED, ENDED], TODAY)).toBe(20);
  });
});

describe('nextPaymentDate', () => {
  it('is the soonest booked from today on', () => {
    const payments = [payment('s', '2026-12-01'), payment('s', TODAY), payment('s', '2026-11-01')];

    expect(nextPaymentDate(payments, 's', TODAY)).toBe(TODAY);
  });

  it('ignores other subscriptions', () => {
    expect(nextPaymentDate([payment('other', '2026-12-01')], 's', TODAY)).toBeUndefined();
  });

  it('ignores the income leg of a contribution', () => {
    const income = { ...payment('s', '2026-12-01'), payment_type: 'income' as const };

    expect(nextPaymentDate([income], 's', TODAY)).toBeUndefined();
  });
});

describe('bookedCount', () => {
  it('counts past and future payments of the subscription', () => {
    const payments = [payment('s', '2026-10-01'), payment('s', '2026-12-01'), payment(null, TODAY)];

    expect(bookedCount(payments, 's')).toBe(2);
  });
});
