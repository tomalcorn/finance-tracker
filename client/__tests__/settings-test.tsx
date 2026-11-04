import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen, waitFor, within } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { queryCache } from '@/composition/queryCache';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const JOINT_ACCOUNT_ID = '6f708192-0000-4000-8000-000000000001';
const PERSONAL_SETTINGS_ID = '8a9b0c1d-0000-4000-8000-000000000001';
const JOINT_SETTINGS_ID = '8a9b0c1d-0000-4000-8000-000000000002';

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: USER_ID, email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

const OWNED = {
  user_id: USER_ID,
  name: '',
  _created_at: CREATED_AT,
  ownership_type: 'personal',
  joint_account_id: null,
};

const JOINT = { ...OWNED, ownership_type: 'joint', joint_account_id: JOINT_ACCOUNT_ID };

let tables: Record<string, StoredRow[]>;
let writes: StoredRow[];
let setups: unknown[];
let writeFailure: GatewayError | null;
let setupFailure: Record<string, GatewayError>;

function memoryGateway(): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert(table, rows) {
      if (writeFailure) throw writeFailure;
      const stored = tables[table] ?? [];
      for (const row of rows as StoredRow[]) {
        writes.push(row);
        const index = stored.findIndex((existing) => existing.id === row.id);
        stored.splice(index === -1 ? stored.length : index, 1, {
          ...row,
          _created_at: CREATED_AT,
        });
      }
      tables[table] = stored;
    },
    async delete() {},
    async call(name, args) {
      if (name !== 'initialise_workspace') return;
      setups.push(args);
      const failure = setupFailure[String(args.p_ownership)];
      if (failure) throw failure;
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

async function choiceIn(group: string, label: string) {
  const control = await screen.findByLabelText(group);
  return within(control).getByRole('radio', { name: label });
}

beforeEach(() => {
  writes = [];
  setups = [];
  writeFailure = null;
  setupFailure = {};
  tables = {
    joint_accounts: [{ id: JOINT_ACCOUNT_ID, name: 'Household' }],
    user_settings: [
      { ...OWNED, id: PERSONAL_SETTINGS_ID, income_roll_up_period: 'current_month' },
      { ...JOINT, id: JOINT_SETTINGS_ID, income_roll_up_period: 'previous_month' },
    ],
    categories_view: [],
    income_sources_view: [],
    bank_accounts_view: [],
    payments: [],
    subscriptions_view: [],
    quick_buttons: [],
  };
});

describe('income month', () => {
  it('shows what is stored for each half', async () => {
    await renderAt('/settings');

    expect(await choiceIn('Joint income month', 'Last month')).toBeChecked();
  });

  it('saves a change straight away', async () => {
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));

    await waitFor(() =>
      expect(tables.user_settings?.find((row) => row.id === PERSONAL_SETTINGS_ID)).toMatchObject({
        income_roll_up_period: 'previous_month',
      }),
    );
  });

  it('leaves the other half alone', async () => {
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));

    await screen.findByText('Personal income now rolls up over last month.');
    expect(writes.map((row) => row.id)).toEqual([PERSONAL_SETTINGS_ID]);
  });

  it('saves the joint half on its own row', async () => {
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Joint income month', 'This month'));

    await screen.findByText('Joint income now rolls up over this month.');
    expect(writes.map((row) => row.id)).toEqual([JOINT_SETTINGS_ID]);
  });

  it('confirms a change', async () => {
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));

    expect(
      await screen.findByText('Personal income now rolls up over last month.'),
    ).toBeOnTheScreen();
  });

  it('writes nothing when the current choice is pressed again', async () => {
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'This month'));

    expect(writes).toEqual([]);
  });

  it('creates the row if there is none yet', async () => {
    tables.user_settings = [];
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));

    await waitFor(() =>
      expect(writes).toEqual([
        expect.objectContaining({
          income_roll_up_period: 'previous_month',
          ownership_type: 'personal',
          user_id: USER_ID,
        }),
      ]),
    );
  });

  it('shows why a change could not be saved', async () => {
    writeFailure = new GatewayError('the database is away');
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));

    expect(await screen.findByText(/^Could not save that setting/)).toBeOnTheScreen();
  });

  it('goes back to what is stored after a failed save', async () => {
    writeFailure = new GatewayError('the database is away');
    await renderAt('/settings');

    await fireEvent.press(await choiceIn('Personal income month', 'Last month'));
    await screen.findByText(/^Could not save that setting/);

    expect(await choiceIn('Personal income month', 'This month')).toBeChecked();
  });
});

describe('joint section', () => {
  it('names the shared account', async () => {
    await renderAt('/settings');

    expect(await screen.findByText('Shared account · Household')).toBeOnTheScreen();
  });

  it('explains when there is no joint account', async () => {
    tables.joint_accounts = [];

    await renderAt('/settings');

    expect(await screen.findByText(/^You don’t have a joint account yet/)).toBeOnTheScreen();
  });

  it('offers no joint setting without a joint account', async () => {
    tables.joint_accounts = [];
    await renderAt('/settings');
    await screen.findByText(/^You don’t have a joint account yet/);

    expect(screen.queryByLabelText('Joint income month')).toBeNull();
  });
});

describe('account', () => {
  it('says who is signed in', async () => {
    await renderAt('/settings');

    expect(await screen.findByText('test@example.com')).toBeOnTheScreen();
  });

  it('offers logging out', async () => {
    await renderAt('/settings');

    expect(await screen.findByRole('button', { name: 'Log out' })).toBeOnTheScreen();
  });
});

describe('first-run setup', () => {
  it.each(['personal', 'joint'])('sets up the %s half when the app opens', async (half) => {
    await renderAt('/settings');

    await waitFor(() => expect(setups).toContainEqual({ p_user_id: USER_ID, p_ownership: half }));
  });

  it('shows why setup failed', async () => {
    setupFailure = { personal: new GatewayError('no permission') };

    await renderAt('/personal');

    expect(await screen.findByText(/^Could not finish setting up/)).toBeOnTheScreen();
  });

  it('doesn’t let a joint failure block the personal half', async () => {
    setupFailure = { joint: new GatewayError('no permission') };
    await renderAt('/personal');
    await screen.findByText('Income split');

    expect(screen.queryByText(/^Could not finish setting up/)).toBeNull();
  });

  it('shows a joint failure on the joint half', async () => {
    setupFailure = { joint: new GatewayError('no permission') };

    await renderAt('/joint');

    expect(await screen.findByText(/^Could not finish setting up/)).toBeOnTheScreen();
  });
});
