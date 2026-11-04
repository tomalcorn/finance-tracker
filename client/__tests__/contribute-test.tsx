import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { queryCache } from '@/composition/queryCache';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { today } from '@/domain/entities';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const MONZO_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const JOINT_BANK_ID = '3c4d5e6f-0000-4000-8000-000000000002';
const JOINT_ACCOUNT_ID = '6f708192-0000-4000-8000-000000000001';
const JOINT_TRACKER_ID = '1a2b3c4d-0000-4000-8000-000000000001';
const EXPENSES_ID = '1a2b3c4d-0000-4000-8000-000000000002';
const SOURCE_ID = '2b3c4d5e-0000-4000-8000-000000000001';

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

function tracker(id: string, name: string, owned: StoredRow = OWNED) {
  return {
    ...owned,
    id,
    name,
    parent_id: null,
    budget: 500,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: 500,
    progress: 0,
    split: 0,
  };
}

function bankAccount(id: string, name: string, owned: StoredRow = OWNED) {
  return { ...owned, id, name, starting_balance: 0, current_balance: 0 };
}

let tables: Record<string, StoredRow[]>;
let calls: { name: string; args: unknown }[];
let callFailure: GatewayError | null;

function memoryGateway(): TableGateway {
  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert() {},
    async delete() {},
    async call(name, args) {
      if (name !== 'contribute_to_joint') return;
      if (callFailure) throw callFailure;
      calls.push({ name, args });
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

async function openForm() {
  await renderAt(`/personal/tracker/${JOINT_TRACKER_ID}`);
  await fireEvent.press(await screen.findByRole('button', { name: 'Contribute' }));
}

beforeEach(() => {
  calls = [];
  callFailure = null;
  tables = {
    joint_accounts: [{ id: JOINT_ACCOUNT_ID, name: 'Household' }],
    categories_view: [
      tracker(JOINT_TRACKER_ID, 'Joint'),
      tracker(EXPENSES_ID, 'Expenses'),
      tracker('1a2b3c4d-0000-4000-8000-000000000003', 'Joint', JOINT),
    ],
    bank_accounts_view: [
      bankAccount(MONZO_ID, 'Monzo'),
      bankAccount(JOINT_BANK_ID, 'Joint Santander', JOINT),
    ],
    income_sources_view: [
      {
        ...JOINT,
        id: SOURCE_ID,
        name: 'Contributions',
        budget_tracker_ids: [],
        current_month: 0,
        income_roll_up_period: 'current_month',
      },
    ],
    payments: [],
    subscriptions_view: [],
    quick_buttons: [],
  };
});

describe('where Contribute is offered', () => {
  it('is on the personal Joint tracker', async () => {
    await renderAt(`/personal/tracker/${JOINT_TRACKER_ID}`);

    expect(await screen.findByRole('button', { name: 'Contribute' })).toBeOnTheScreen();
  });

  it('isn’t on another tracker', async () => {
    await renderAt(`/personal/tracker/${EXPENSES_ID}`);
    await screen.findByText('Change budget');

    expect(screen.queryByRole('button', { name: 'Contribute' })).toBeNull();
  });

  it('isn’t on the joint half', async () => {
    await renderAt('/joint/tracker/1a2b3c4d-0000-4000-8000-000000000003');
    await screen.findByText('Change budget');

    expect(screen.queryByRole('button', { name: 'Contribute' })).toBeNull();
  });

  it('isn’t offered without a joint account', async () => {
    tables.joint_accounts = [];
    await renderAt(`/personal/tracker/${JOINT_TRACKER_ID}`);
    await screen.findByText('Change budget');

    expect(screen.queryByRole('button', { name: 'Contribute' })).toBeNull();
  });
});

describe('the form', () => {
  it('asks for a joint bank account first', async () => {
    tables.bank_accounts_view = [bankAccount(MONZO_ID, 'Monzo')];

    await openForm();

    expect(await screen.findByText(/need a joint bank account/)).toBeOnTheScreen();
  });

  it('asks for a joint income source first', async () => {
    tables.income_sources_view = [];

    await openForm();

    expect(await screen.findByText(/need a joint income source/)).toBeOnTheScreen();
  });

  it('calls the database function with what was entered', async () => {
    await openForm();

    await fireEvent.changeText(await screen.findByLabelText('Amount'), '150.50');
    await fireEvent.press(screen.getAllByRole('button', { name: 'Contribute' }).at(-1)!);

    await waitFor(() =>
      expect(calls).toEqual([
        {
          name: 'contribute_to_joint',
          args: {
            p_user_id: USER_ID,
            p_amount: 150.5,
            p_from_bank_account_id: MONZO_ID,
            p_to_bank_account_id: JOINT_BANK_ID,
            p_income_source_id: SOURCE_ID,
            p_payment_date: today(),
          },
        },
      ]),
    );
  });

  it('says where the money went', async () => {
    await openForm();

    await fireEvent.changeText(await screen.findByLabelText('Amount'), '150');
    await fireEvent.press(screen.getAllByRole('button', { name: 'Contribute' }).at(-1)!);

    expect(await screen.findByText('£150.00 contributed to Household')).toBeOnTheScreen();
  });

  it('writes nothing without an amount', async () => {
    await openForm();
    await screen.findByLabelText('Amount');

    await fireEvent.press(screen.getAllByRole('button', { name: 'Contribute' }).at(-1)!);

    await screen.findByText('Enter the amount.');
    expect(calls).toEqual([]);
  });

  it('shows why the database refused', async () => {
    callFailure = new GatewayError('You have no Joint budget tracker');
    await openForm();

    await fireEvent.changeText(await screen.findByLabelText('Amount'), '150');
    await fireEvent.press(screen.getAllByRole('button', { name: 'Contribute' }).at(-1)!);

    expect(await screen.findByText(/no Joint budget tracker/)).toBeOnTheScreen();
  });
});
