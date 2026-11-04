import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import { queryCache } from '@/composition/queryCache';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { today } from '@/domain/entities';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const MONZO_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const AMEX_ID = '3c4d5e6f-0000-4000-8000-000000000002';
const JOINT_BANK_ID = '3c4d5e6f-0000-4000-8000-000000000003';
const JOINT_ACCOUNT_ID = '6f708192-0000-4000-8000-000000000001';
const JOINT_SOURCE_ID = '2b3c4d5e-0000-4000-8000-000000000001';
const SUBSCRIPTION_ID = '5e6f7081-0000-4000-8000-000000000001';
const BUTTON_ID = '7a8b9c0d-0000-4000-8000-000000000001';

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

function account(id: string, name: string, startingBalance: number, currentBalance: number) {
  return {
    ...OWNED,
    id,
    name,
    starting_balance: startingBalance,
    current_balance: currentBalance,
  };
}

function payment(bankAccountId: string) {
  return {
    ...OWNED,
    id: '4d5e6f70-0000-4000-8000-000000000001',
    name: 'Coffee',
    payment_date: '2026-10-01',
    payment_type: 'expense',
    expense: 3,
    income: 0,
    checked: false,
    bank_account_id: bankAccountId,
    category_id: null,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

function subscription(overrides: StoredRow) {
  return {
    ...OWNED,
    id: SUBSCRIPTION_ID,
    name: 'Netflix',
    amount: 10,
    cadence: 'monthly',
    bank_account_id: MONZO_ID,
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

let tables: Record<string, StoredRow[]>;
let deleteFailure: GatewayError | null;

/** A database in memory. A write to `bank_accounts` is mirrored into its view. */
function memoryGateway(): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert(table, rows) {
      const name = table === 'bank_accounts' ? 'bank_accounts_view' : table;
      const stored = tables[name] ?? [];
      for (const row of rows as StoredRow[]) {
        const index = stored.findIndex((existing) => existing.id === row.id);
        stored.splice(index === -1 ? stored.length : index, 1, {
          current_balance: row.starting_balance,
          _created_at: CREATED_AT,
          ...row,
        });
      }
      tables[name] = stored;
    },
    async delete(table, ids) {
      if (deleteFailure) throw deleteFailure;
      const name = table === 'bank_accounts' ? 'bank_accounts_view' : table;
      tables[name] = (tables[name] ?? []).filter((row) => !ids.includes(row.id as string));
    },
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
  deleteFailure = null;
  tables = {
    bank_accounts_view: [
      account(MONZO_ID, 'Monzo', 1000, 1250.5),
      account(AMEX_ID, 'Amex', 0, -200),
    ],
    categories_view: [],
    income_sources_view: [],
    payments: [],
    subscriptions_view: [],
    quick_buttons: [],
  };
});

describe('tiles', () => {
  it('shows the total across accounts', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('£1,050.50 total')).toBeOnTheScreen();
  });

  it('shows what each account holds', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('-£200.00')).toBeOnTheScreen();
  });

  it('says how an account has moved', async () => {
    tables.payments = [{ ...payment(MONZO_ID), payment_date: today() }];

    await renderAt('/personal');

    expect(
      await screen.findByRole('button', { name: /^Monzo, £1,250\.50, -£3 / }),
    ).toBeOnTheScreen();
  });

  it('shows why the trends could not load', async () => {
    tables.payments = [{ ...OWNED, id: 'not-a-row' }];

    await renderAt('/personal');

    expect(await screen.findByText(/^Could not load the trends/)).toBeOnTheScreen();
  });

  it('invites adding the first account', async () => {
    tables.bank_accounts_view = [];

    await renderAt('/personal');

    expect(await screen.findByText(/^No bank accounts yet\. Add one/)).toBeOnTheScreen();
  });

  it('shows why the accounts could not load', async () => {
    tables.bank_accounts_view = [{ ...OWNED, id: 'not-a-row' }];

    await renderAt('/personal');

    expect(await screen.findByText(/^Could not load your accounts/)).toBeOnTheScreen();
  });

  it('keeps each half to its own accounts', async () => {
    tables.joint_accounts = [{ id: JOINT_ACCOUNT_ID, name: 'Household' }];
    tables.bank_accounts_view?.push({
      ...account(JOINT_BANK_ID, 'Joint Santander', 0, 75),
      ...JOINT,
    });

    await renderAt('/joint');

    expect(await screen.findByText('£75.00 total')).toBeOnTheScreen();
  });
});

describe('adding', () => {
  async function openNew() {
    await renderAt('/personal');
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a bank account' }));
  }

  it('writes the account', async () => {
    await openNew();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'Saver');
    await fireEvent.changeText(screen.getByLabelText('Starting balance'), '500');
    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    await screen.findByText('Saver added');
    expect(tables.bank_accounts_view?.find((row) => row.name === 'Saver')).toMatchObject({
      starting_balance: 500,
      ownership_type: 'personal',
      user_id: USER_ID,
    });
  });

  it('takes a balance below zero', async () => {
    await openNew();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'Barclaycard');
    await fireEvent.changeText(screen.getByLabelText('Starting balance'), '-120.50');
    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    await screen.findByText('Barclaycard added');
    expect(tables.bank_accounts_view?.find((row) => row.name === 'Barclaycard')).toMatchObject({
      starting_balance: -120.5,
    });
  });

  it('asks for a starting balance', async () => {
    await openNew();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'Saver');
    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    expect(await screen.findByText('Enter the starting balance, or 0.')).toBeOnTheScreen();
  });

  it('writes nothing without a starting balance', async () => {
    await openNew();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'Saver');
    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));

    expect(tables.bank_accounts_view).toHaveLength(2);
  });
});

describe('editing', () => {
  async function openMonzo() {
    await renderAt('/personal');
    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));
  }

  it('saves a new name and starting balance', async () => {
    await openMonzo();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'Monzo Joint-ish');
    await fireEvent.changeText(screen.getByLabelText('Starting balance'), '1100');
    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(tables.bank_accounts_view?.find((row) => row.id === MONZO_ID)).toMatchObject({
        name: 'Monzo Joint-ish',
        starting_balance: 1100,
      }),
    );
  });

  it('shows the current balance as read-only help', async () => {
    await openMonzo();

    expect(await screen.findByText(/current balance, £1,250\.50, is this plus/)).toBeOnTheScreen();
  });
});

describe('deleting', () => {
  it('removes an unused account after confirming', async () => {
    await renderAt('/personal');
    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));
    await fireEvent.press(await screen.findByRole('button', { name: 'Delete' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    await screen.findByText('Monzo deleted');
    expect(tables.bank_accounts_view?.map((row) => row.id)).toEqual([AMEX_ID]);
  });

  it('warns that its quick buttons go too', async () => {
    tables.quick_buttons = [
      {
        ...OWNED,
        id: BUTTON_ID,
        name: 'Coffee',
        icon: null,
        display_order: 0,
        mode: 'log',
        payment_name: null,
        expense: 3,
        bank_account_id: MONZO_ID,
        category_id: null,
      },
    ];
    await renderAt('/personal');
    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));

    await fireEvent.press(await screen.findByRole('button', { name: 'Delete' }));

    expect(await screen.findByText(/quick button that logs to it goes too/)).toBeOnTheScreen();
  });

  it('isn’t offered with a payment on the account', async () => {
    tables.payments = [payment(MONZO_ID)];
    await renderAt('/personal');

    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));

    expect(await screen.findByText(/can’t be deleted while payments/)).toBeOnTheScreen();
  });

  it('isn’t offered with a subscription on the account', async () => {
    tables.subscriptions_view = [subscription({})];
    await renderAt('/personal');

    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));

    expect(await screen.findByText(/can’t be deleted while payments/)).toBeOnTheScreen();
  });

  it('isn’t offered for a joint account a personal contribution arrives in', async () => {
    tables.joint_accounts = [{ id: JOINT_ACCOUNT_ID, name: 'Household' }];
    tables.bank_accounts_view?.push({
      ...account(JOINT_BANK_ID, 'Joint Santander', 0, 75),
      ...JOINT,
    });
    tables.subscriptions_view = [
      subscription({
        joint_bank_account_id: JOINT_BANK_ID,
        joint_income_source_id: JOINT_SOURCE_ID,
      }),
    ];
    await renderAt('/joint');

    await fireEvent.press(await screen.findByRole('button', { name: /^Joint Santander/ }));

    expect(await screen.findByText(/can’t be deleted while payments/)).toBeOnTheScreen();
  });

  it('shows why the database refused', async () => {
    deleteFailure = new GatewayError('violates foreign key constraint');
    await renderAt('/personal');
    await fireEvent.press(await screen.findByRole('button', { name: /^Monzo/ }));
    await fireEvent.press(await screen.findByRole('button', { name: 'Delete' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByText(/violates foreign key constraint/)).toBeOnTheScreen();
  });
});
