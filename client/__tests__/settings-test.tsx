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

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: USER_ID, email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
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
        const createdAt = stored[index]?._created_at ?? '2026-10-25T12:00:00.000000+00:00';
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

function renderSettings() {
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
    initialUrl: '/settings',
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

beforeEach(() => {
  tables = {
    quick_buttons: [
      {
        id: '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01',
        user_id: USER_ID,
        name: 'Coffee',
        _created_at: '2026-10-01T09:30:12.345678+00:00',
        ownership_type: 'personal',
        joint_account_id: null,
        mode: 'prompt',
        payment_name: null,
        expense: null,
        bank_account_id: null,
        category_id: null,
        icon: null,
        display_order: 0,
      },
    ],
  };
});

describe('quick-button probe', () => {
  it('adds a button and shows it once saved', async () => {
    await renderSettings();

    await fireEvent.press(await screen.findByText('Add a probe button'));

    expect(await screen.findByText('Quick buttons: 2')).toBeOnTheScreen();
  });

  it('edits a button it made', async () => {
    await renderSettings();
    await fireEvent.press(await screen.findByText('Add a probe button'));
    await screen.findByText('Quick buttons: 2');

    await fireEvent.press(screen.getByText('Add £1 to the first'));

    expect(await screen.findByText('£2.50')).toBeOnTheScreen();
  });

  it('deletes only the buttons it made', async () => {
    await renderSettings();
    await fireEvent.press(await screen.findByText('Add a probe button'));
    await screen.findByText('Quick buttons: 2');

    await fireEvent.press(screen.getByText('Delete probe buttons'));

    expect(await screen.findByText('Quick buttons: 1')).toBeOnTheScreen();
  });
});
