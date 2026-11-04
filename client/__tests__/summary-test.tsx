import { QueryClient } from '@tanstack/react-query';
import { renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { queryCache } from '@/composition/queryCache';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import type { StoredRow, TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { today } from '@/domain/entities';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const ACCOUNT_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const JOINT_BANK_ID = '3c4d5e6f-0000-4000-8000-000000000002';
const JOINT_ACCOUNT_ID = '6f708192-0000-4000-8000-000000000001';
const TRACKER_ID = '1a2b3c4d-0000-4000-8000-000000000001';

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

function tracker(overrides: StoredRow) {
  return {
    ...OWNED,
    id: TRACKER_ID,
    name: 'Expenses',
    parent_id: null,
    budget: 2000,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 1200,
    remaining: 800,
    progress: 60,
    split: 0,
    ...overrides,
  };
}

let tables: Record<string, StoredRow[]>;

function memoryGateway(): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert() {},
    async delete() {},
    async call() {},
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

beforeEach(() => {
  tables = {
    bank_accounts_view: [
      {
        ...OWNED,
        id: ACCOUNT_ID,
        name: 'Monzo',
        starting_balance: 0,
        current_balance: 4136.75,
      },
    ],
    categories_view: [tracker({})],
    income_sources_view: [],
    payments: [
      {
        ...OWNED,
        id: '4d5e6f70-0000-4000-8000-000000000001',
        name: 'Tesco',
        payment_date: today(),
        payment_type: 'expense',
        expense: 45,
        income: 0,
        checked: false,
        bank_account_id: ACCOUNT_ID,
        category_id: null,
        income_source_id: null,
        subscription_id: null,
        linked_payment_id: null,
      },
    ],
    subscriptions_view: [],
    quick_buttons: [],
  };
});

describe('summary', () => {
  it('names the total balance', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('Total balance')).toBeOnTheScreen();
  });

  it('shows what is left of the budget', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('40% of £2,000')).toBeOnTheScreen();
  });

  it('says when no budget is set', async () => {
    tables.categories_view = [tracker({ budget: 0, remaining: 0 })];

    await renderAt('/personal');

    expect(await screen.findByText('no budget set')).toBeOnTheScreen();
  });

  it('compares this month’s spending with last month’s', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('+£45 vs last month')).toBeOnTheScreen();
  });

  it('shows why it could not load', async () => {
    tables.payments = [{ ...OWNED, id: 'not-a-row' }];

    await renderAt('/personal');

    expect(await screen.findByText(/^Could not load your summary/)).toBeOnTheScreen();
  });

  it('keeps each half to its own figures', async () => {
    tables.joint_accounts = [{ id: JOINT_ACCOUNT_ID, name: 'Household' }];
    tables.categories_view?.push(
      tracker({
        ...JOINT,
        id: '1a2b3c4d-0000-4000-8000-000000000002',
        budget: 500,
        remaining: 250,
      }),
    );
    tables.bank_accounts_view?.push({
      ...JOINT,
      id: JOINT_BANK_ID,
      name: 'Joint Santander',
      starting_balance: 0,
      current_balance: 75,
    });

    await renderAt('/joint');

    expect(await screen.findByText('50% of £500')).toBeOnTheScreen();
  });
});
