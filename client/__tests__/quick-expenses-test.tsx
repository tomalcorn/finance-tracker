import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import { queryCache } from '@/composition/queryCache';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import type { StoredRow, TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';
const JOINT_ID = '9a3d6e1f-4c2b-4f7a-8e5d-1b6c3a9f2e08';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';

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

const COFFEE: StoredRow = {
  ...OWNED,
  id: '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01',
  name: 'Coffee',
  mode: 'log',
  payment_name: null,
  expense: 3.4,
  bank_account_id: BANK_ACCOUNT_ID,
  category_id: null,
  icon: '☕',
  display_order: 0,
};

const GROCERIES: StoredRow = {
  ...COFFEE,
  id: '6a3c2d0f-9e4b-4c7a-8f2e-3d8b5c9f7a12',
  name: 'Groceries',
  mode: 'prompt',
  expense: null,
  bank_account_id: null,
  icon: null,
  display_order: 1,
};

/** A database in memory: upserted rows are stored by id, stamped as the database would. */
function memoryGateway(tables: Record<string, StoredRow[]>): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert(table, rows) {
      const stored = tables[table] ?? [];
      for (const row of rows as StoredRow[]) {
        const index = stored.findIndex((existing) => existing.id === row.id);
        const createdAt = stored[index]?._created_at ?? CREATED_AT;
        stored.splice(index === -1 ? stored.length : index, 1, { ...row, _created_at: createdAt });
      }
      tables[table] = stored;
    },
    async delete(table, ids) {
      tables[table] = (tables[table] ?? []).filter((row) => !ids.includes(row.id as string));
    },
  };
}

let tables: Record<string, StoredRow[]>;

function renderQuickExpenses() {
  const create = (): Services => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const gateway = memoryGateway(tables);
    const cache = queryCache(queryClient);
    return {
      auth: SIGNED_IN_AUTH,
      queryClient,
      repositories: (userId) => createRepositories({ userId, gateway, cache }),
    };
  };
  return renderRouter(APP_DIR, {
    initialUrl: '/',
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

/** Rows of a table, without the columns stamped by the database. */
function stored(table: string) {
  return tables[table] ?? [];
}

beforeEach(() => {
  tables = {
    quick_buttons: [COFFEE, GROCERIES],
    bank_accounts_view: [
      { ...OWNED, id: BANK_ACCOUNT_ID, name: 'Current', starting_balance: 0, current_balance: 0 },
    ],
  };
});

describe('logging', () => {
  it('logs a button’s preset payment when tapped', async () => {
    await renderQuickExpenses();

    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));

    expect(stored('payments')).toEqual([
      expect.objectContaining({ name: 'Coffee', expense: 3.4, payment_type: 'expense' }),
    ]);
  });

  it('confirms what it logged', async () => {
    await renderQuickExpenses();

    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));

    expect(await screen.findByText('Coffee — £3.40 logged')).toBeOnTheScreen();
  });

  it('takes the payment back on Undo', async () => {
    await renderQuickExpenses();
    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));

    await fireEvent.press(await screen.findByRole('button', { name: 'Undo' }));

    expect(await screen.findByText('Payment removed')).toBeOnTheScreen();
  });

  it('removes the payment on Undo', async () => {
    await renderQuickExpenses();
    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));
    await fireEvent.press(await screen.findByRole('button', { name: 'Undo' }));
    await screen.findByText('Payment removed');

    expect(stored('payments')).toEqual([]);
  });

  it('asks for the details a prompt button leaves out, then logs them', async () => {
    await renderQuickExpenses();
    await fireEvent.press(await screen.findByRole('button', { name: 'Groceries' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Tesco');
    await fireEvent.changeText(screen.getByLabelText('Amount'), '46.20');
    await fireEvent.press(screen.getByRole('button', { name: 'Bank account' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Current' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Log payment' }));

    expect(stored('payments')).toEqual([
      expect.objectContaining({ name: 'Tesco', expense: 46.2, bank_account_id: BANK_ACCOUNT_ID }),
    ]);
  });
});

describe('managing buttons', () => {
  it('adds a button', async () => {
    await renderQuickExpenses();
    await fireEvent.press(await screen.findByRole('button', { name: 'Edit' }));
    await fireEvent.press(screen.getByRole('button', { name: 'New button' }));
    await fireEvent.changeText(screen.getByLabelText('Button name'), 'Bus');
    await fireEvent.press(screen.getByRole('radio', { name: 'Ask first' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByRole('button', { name: 'Edit Bus' })).toBeOnTheScreen();
  });

  it('edits a button held down', async () => {
    await renderQuickExpenses();
    await fireEvent(await screen.findByRole('button', { name: 'Coffee' }), 'longPress');
    await fireEvent.changeText(screen.getByLabelText('Amount'), '3.60');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByText('£3.60')).toBeOnTheScreen();
  });

  it('removes a button once confirmed', async () => {
    await renderQuickExpenses();
    await fireEvent(await screen.findByRole('button', { name: 'Coffee' }), 'longPress');
    await fireEvent.press(screen.getByRole('button', { name: 'Remove button' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Remove button' }));

    expect(await screen.findByText('Coffee removed')).toBeOnTheScreen();
  });

  it('won’t save a button that logs at once without an amount', async () => {
    await renderQuickExpenses();
    await fireEvent(await screen.findByRole('button', { name: 'Coffee' }), 'longPress');
    await fireEvent.changeText(screen.getByLabelText('Amount'), '');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(screen.getByText('A button that logs at once needs an amount.')).toBeOnTheScreen();
  });

  it('offers to add the first button when there are none', async () => {
    tables.quick_buttons = [];

    await renderQuickExpenses();

    expect(await screen.findByRole('button', { name: 'Add a quick button' })).toBeOnTheScreen();
  });
});

describe('ownership', () => {
  it('offers no choice of ledger without a joint account', async () => {
    await renderQuickExpenses();
    await screen.findByRole('button', { name: 'Coffee' });

    expect(screen.queryByRole('radio', { name: 'Joint' })).not.toBeOnTheScreen();
  });

  it('shows the joint account’s buttons once Joint is chosen', async () => {
    tables.joint_accounts = [{ id: JOINT_ID, name: 'Home' }];
    tables.quick_buttons = [
      COFFEE,
      {
        ...COFFEE,
        id: '7b4d3e1a-0f5c-4d8b-9a3f-4e9c6d0a8b23',
        name: 'Rent',
        ownership_type: 'joint',
        joint_account_id: JOINT_ID,
      },
    ];
    await renderQuickExpenses();

    await fireEvent.press(await screen.findByRole('radio', { name: 'Joint' }));

    expect(await screen.findByRole('button', { name: 'Rent' })).toBeOnTheScreen();
  });
});
