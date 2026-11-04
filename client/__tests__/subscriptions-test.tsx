import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import { queryCache } from '@/composition/queryCache';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import type { StoredRow, TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const BANK_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const JOINT_BANK_ID = '3c4d5e6f-0000-4000-8000-000000000002';
const JOINT_TRACKER_ID = '1a2b3c4d-0000-4000-8000-000000000001';
const JOINT_ACCOUNT_ID = '6f708192-0000-4000-8000-000000000001';
const JOINT_SOURCE_ID = '2b3c4d5e-0000-4000-8000-000000000001';
const NETFLIX_ID = '5e6f7081-0000-4000-8000-000000000001';
const TO_JOINT_ID = '5e6f7081-0000-4000-8000-000000000002';
const YEARLY_ID = '5e6f7081-0000-4000-8000-000000000003';
const STOPPED_ID = '5e6f7081-0000-4000-8000-000000000004';

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: USER_ID, email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

const OWNED = {
  user_id: USER_ID,
  _created_at: CREATED_AT,
  ownership_type: 'personal',
  joint_account_id: null,
};

const JOINT = { ...OWNED, ownership_type: 'joint', joint_account_id: JOINT_ACCOUNT_ID };

function subscription(id: string, name: string, amount: number, overrides: StoredRow = {}) {
  return {
    ...OWNED,
    id,
    name,
    amount,
    cadence: 'monthly',
    bank_account_id: BANK_ID,
    category_id: null,
    start_date: '2026-01-01',
    end_date: null,
    is_active: true,
    monthly_cost: amount,
    joint_income_source_id: null,
    joint_bank_account_id: null,
    ...overrides,
  };
}

let tables: Record<string, StoredRow[]>;
let reconciled: Record<string, string | number>[];

/** A database in memory. A write to `subscriptions` is mirrored into its view. */
function memoryGateway(): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert(table, rows) {
      const name = table === 'subscriptions' ? 'subscriptions_view' : table;
      const stored = tables[name] ?? [];
      for (const row of rows as StoredRow[]) {
        const index = stored.findIndex((existing) => existing.id === row.id);
        stored.splice(index === -1 ? stored.length : index, 1, {
          monthly_cost: row.amount,
          _created_at: CREATED_AT,
          ...row,
        });
      }
      tables[name] = stored;
    },
    async delete(table, ids) {
      const name = table === 'subscriptions' ? 'subscriptions_view' : table;
      tables[name] = (tables[name] ?? []).filter((row) => !ids.includes(row.id as string));
    },
    async call(name, args) {
      if (name === 'reconcile_subscriptions') reconciled.push({ ...args });
    },
  };
}

function renderAt(initialUrl: string) {
  const create = (): Services => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const gateway = memoryGateway();
    const cache = queryCache(queryClient);
    return {
      auth: SIGNED_IN_AUTH,
      queryClient,
      repositories: (userId) => createRepositories({ userId, gateway, cache }),
    };
  };
  return renderRouter(APP_DIR, {
    initialUrl,
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

/** Give the user a joint account, with somewhere for a contribution's income to go. */
function joinJointAccount() {
  tables.joint_accounts = [{ id: JOINT_ACCOUNT_ID, name: 'Household' }];
  tables.bank_accounts_view?.push({
    ...JOINT,
    id: JOINT_BANK_ID,
    name: 'Joint Santander',
    starting_balance: 0,
    current_balance: 0,
  });
  tables.income_sources_view = [
    {
      ...JOINT,
      id: JOINT_SOURCE_ID,
      name: 'Contributions',
      budget_tracker_ids: [],
      current_month: 0,
      income_roll_up_period: 'current_month',
    },
  ];
}

beforeEach(() => {
  reconciled = [];
  tables = {
    subscriptions_view: [
      subscription(NETFLIX_ID, 'Netflix', 9.99),
      subscription(TO_JOINT_ID, 'To joint', 500, {
        category_id: JOINT_TRACKER_ID,
        joint_bank_account_id: JOINT_BANK_ID,
        joint_income_source_id: JOINT_SOURCE_ID,
      }),
    ],
    bank_accounts_view: [
      { ...OWNED, id: BANK_ID, name: 'Monzo', starting_balance: 0, current_balance: 0 },
    ],
    categories_view: [
      {
        ...OWNED,
        id: JOINT_TRACKER_ID,
        name: 'Joint',
        parent_id: null,
        accrual: 'monthly',
        budget: 0,
        cost: 0,
        starting_balance: 0,
        accrued: 0,
        remaining: 0,
        progress: 0,
        split: 0,
      },
    ],
    income_sources_view: [],
    payments: [],
  };
});

describe('reconciling', () => {
  it('runs for both halves when the app opens', async () => {
    await renderAt('/personal');

    await waitFor(() =>
      expect(reconciled).toEqual([
        { p_user_id: USER_ID, p_ownership: 'personal' },
        { p_user_id: USER_ID, p_ownership: 'joint' },
      ]),
    );
  });

  it('runs again after a change is saved', async () => {
    await renderAt('/personal/subscriptions');
    await waitFor(() => expect(reconciled).toHaveLength(2));
    await fireEvent.press(await screen.findByRole('button', { name: /^Netflix/ }));

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(reconciled).toHaveLength(3));
  });
});

describe('overview', () => {
  it('leaves joint contributions out of the monthly total', async () => {
    await renderAt('/personal');

    expect(await screen.findByText(/^£9\.99 a month/)).toBeOnTheScreen();
  });

  it('leaves joint contributions out of the count', async () => {
    await renderAt('/personal');

    expect(await screen.findByText(/1 running$/)).toBeOnTheScreen();
  });

  it('opens the subscriptions', async () => {
    await renderAt('/personal');

    await fireEvent.press(await screen.findByRole('button', { name: 'Subscriptions' }));

    expect(await screen.findByRole('button', { name: /^Netflix/ })).toBeOnTheScreen();
  });
});

describe('what they really cost', () => {
  beforeEach(() => {
    joinJointAccount();
    tables.subscriptions_view?.push(
      subscription(YEARLY_ID, 'Yearly thing', 120, { cadence: 'yearly', monthly_cost: 10 }),
      subscription(STOPPED_ID, 'Old gym', 30, { is_active: false }),
    );
  });

  it('totals the month', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByText('£19.99 a month')).toBeOnTheScreen();
  });

  it('totals the year', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByText('£239.88 a year')).toBeOnTheScreen();
  });

  it('shows each one’s monthly cost, whatever its cadence', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByText('£10.00/mo')).toBeOnTheScreen();
  });

  it('shows what it actually charges', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByText('£120.00 yearly')).toBeOnTheScreen();
  });

  it('puts the dearest first', async () => {
    await renderAt('/personal/subscriptions');

    const rows = await screen.findAllByRole('button', { name: /^(Netflix|Yearly thing)$/ });

    expect(rows.map((row) => row.props.accessibilityLabel)).toEqual(['Yearly thing', 'Netflix']);
  });

  it('sets aside what isn’t running', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByText('Turned off · £30.00 monthly')).toBeOnTheScreen();
  });

  it('shows no total when nothing is running', async () => {
    tables.subscriptions_view = [subscription(STOPPED_ID, 'Old gym', 30, { is_active: false })];

    await renderAt('/personal/subscriptions');
    await screen.findByText('Turned off · £30.00 monthly');

    expect(screen.queryByText(/a month$/)).not.toBeOnTheScreen();
  });
});

describe('without a joint account', () => {
  it('lists a leftover contribution with the rest', async () => {
    await renderAt('/personal/subscriptions');

    expect(await screen.findByRole('button', { name: /^To joint/ })).toBeOnTheScreen();
  });

  it('offers no contributions tab', async () => {
    await renderAt('/personal/subscriptions');
    await screen.findByRole('button', { name: /^Netflix/ });

    expect(screen.queryByRole('radio', { name: 'Joint contributions' })).not.toBeOnTheScreen();
  });
});

describe('with a joint account', () => {
  beforeEach(joinJointAccount);

  it('keeps contributions out of the ordinary list', async () => {
    await renderAt('/personal/subscriptions');
    await screen.findByRole('button', { name: /^Netflix/ });

    expect(screen.queryByRole('button', { name: /^To joint/ })).not.toBeOnTheScreen();
  });

  it('lists them on their own tab', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('radio', { name: 'Joint contributions' }));

    expect(await screen.findByRole('button', { name: /^To joint/ })).toBeOnTheScreen();
  });

  it('offers no tab on the joint half', async () => {
    await renderAt('/joint/subscriptions');
    await screen.findByText(/^No subscriptions yet/);

    expect(screen.queryByRole('radio', { name: 'Joint contributions' })).not.toBeOnTheScreen();
  });

  it('adds a contribution, booked against the Joint tracker', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('radio', { name: 'Joint contributions' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Add a joint contribution' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Standing order');
    await fireEvent.changeText(screen.getByLabelText('Amount'), '250');
    await fireEvent.press(screen.getByRole('button', { name: 'To (joint)' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Joint Santander' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Joint income source' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Contributions' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));
    await screen.findByText('Standing order added');

    expect(tables.subscriptions_view?.at(-1)).toEqual(
      expect.objectContaining({
        category_id: JOINT_TRACKER_ID,
        joint_bank_account_id: JOINT_BANK_ID,
        joint_income_source_id: JOINT_SOURCE_ID,
      }),
    );
  });

  it('asks a contribution for its joint fields', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('radio', { name: 'Joint contributions' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Add a joint contribution' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    expect(screen.getByText('Choose the joint account it arrives in.')).toBeOnTheScreen();
  });
});

describe('adding a subscription', () => {
  it('saves it, from the only account', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a subscription' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Spotify');
    await fireEvent.changeText(screen.getByLabelText('Amount'), '11.99');

    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));
    await screen.findByText('Spotify added');

    expect(tables.subscriptions_view?.at(-1)).toEqual(
      expect.objectContaining({
        name: 'Spotify',
        amount: 11.99,
        cadence: 'monthly',
        bank_account_id: BANK_ID,
        joint_income_source_id: null,
      }),
    );
  });

  it('says what is missing', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a subscription' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    expect(screen.getByText('Give it a name.')).toBeOnTheScreen();
  });
});

describe('editing a subscription', () => {
  it('turns it off', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('button', { name: /^Netflix/ }));

    await fireEvent(screen.getByLabelText('Active'), 'valueChange', false);
    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(tables.subscriptions_view?.find((row) => row.id === NETFLIX_ID)?.is_active).toBe(
        false,
      ),
    );
  });

  it('warns that deleting takes its booked payments with it', async () => {
    tables.payments?.push({
      ...OWNED,
      id: '4d5e6f70-0000-4000-8000-000000000001',
      name: 'Sub: Netflix',
      payment_date: '2026-01-01',
      payment_type: 'expense',
      expense: 9.99,
      income: 0,
      checked: false,
      bank_account_id: BANK_ID,
      category_id: null,
      income_source_id: null,
      subscription_id: NETFLIX_ID,
      linked_payment_id: null,
    });
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('button', { name: /^Netflix/ }));

    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByText(/^The payment it booked go/)).toBeOnTheScreen();
  });

  it('deletes it once confirmed', async () => {
    await renderAt('/personal/subscriptions');
    await fireEvent.press(await screen.findByRole('button', { name: /^Netflix/ }));
    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));
    await screen.findByText('Netflix deleted');

    expect(tables.subscriptions_view?.map((row) => row.id)).toEqual([TO_JOINT_ID]);
  });
});
