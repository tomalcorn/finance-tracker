import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import { queryCache } from '@/composition/queryCache';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import type { StoredRow, TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { today } from '@/domain/entities';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const EXPENSES_ID = '1a2b3c4d-0000-4000-8000-000000000001';
const ONE_OFFS_ID = '1a2b3c4d-0000-4000-8000-000000000002';
const SAVINGS_ID = '1a2b3c4d-0000-4000-8000-000000000003';
const GROCERIES_ID = '1a2b3c4d-0000-4000-8000-000000000004';

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

/** A `categories_view` row, its computed columns filled in for a category with no payments. */
function viewRow(row: StoredRow): StoredRow {
  const budget = Number(row.budget ?? 0);
  return {
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    ...row,
    _created_at: CREATED_AT,
    accrued: 0,
    remaining: budget,
    progress: 0,
    split: 0,
  };
}

/** A database in memory. A write to `categories` is mirrored into `categories_view`. */
function memoryGateway(tables: Record<string, StoredRow[]>): TableGateway {
  function store(table: string, rows: StoredRow[]) {
    const stored = tables[table] ?? [];
    for (const row of rows) {
      const index = stored.findIndex((existing) => existing.id === row.id);
      stored.splice(index === -1 ? stored.length : index, 1, { ...row, _created_at: CREATED_AT });
    }
    tables[table] = stored;
  }

  return {
    async select(source, eq) {
      return (tables[source] ?? []).filter((row) =>
        Object.entries(eq).every(([column, value]) => row[column] === value),
      );
    },
    async upsert(table, rows) {
      store(table, rows as StoredRow[]);
      if (table === 'categories') store('categories_view', (rows as StoredRow[]).map(viewRow));
    },
    async delete(table, ids) {
      const keep = (row: StoredRow) => !ids.includes(row.id as string);
      tables[table] = (tables[table] ?? []).filter(keep);
      if (table === 'categories')
        tables.categories_view = (tables.categories_view ?? []).filter(keep);
    },
  };
}

let tables: Record<string, StoredRow[]>;

function renderAt(initialUrl: string) {
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
    initialUrl,
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

beforeEach(() => {
  tables = {
    categories_view: [
      viewRow({ ...OWNED, id: EXPENSES_ID, name: 'Expenses', parent_id: null, budget: 1200 }),
      viewRow({ ...OWNED, id: ONE_OFFS_ID, name: 'One-offs', parent_id: null, budget: 300 }),
      viewRow({ ...OWNED, id: SAVINGS_ID, name: 'Savings', parent_id: null, budget: 500 }),
      viewRow({
        ...OWNED,
        id: GROCERIES_ID,
        name: 'Groceries',
        parent_id: EXPENSES_ID,
        budget: 400,
      }),
    ],
    income_sources_view: [
      {
        ...OWNED,
        id: '2b3c4d5e-0000-4000-8000-000000000001',
        name: 'Salary',
        budget_tracker_ids: [EXPENSES_ID],
        current_month: 2500,
        income_roll_up_period: 'current_month',
      },
    ],
  };
});

describe('budget overview', () => {
  it('shows the income being split', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('£500.00 not yet allocated')).toBeOnTheScreen();
  });

  it('lists the trackers, with what each has left', async () => {
    await renderAt('/personal');

    expect(await screen.findByText('£1,200.00 left')).toBeOnTheScreen();
  });

  it('opens a tracker’s detail', async () => {
    await renderAt('/personal');

    await fireEvent.press(await screen.findByRole('button', { name: 'Expenses' }));

    expect(await screen.findByRole('button', { name: 'Groceries' })).toBeOnTheScreen();
  });
});

describe('tracker detail', () => {
  it('adds a subcategory', async () => {
    await renderAt(`/personal/tracker/${EXPENSES_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a subcategory' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Transport');
    await fireEvent.changeText(screen.getByLabelText('Monthly budget'), '150');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByRole('button', { name: 'Transport' })).toBeOnTheScreen();
  });

  it('files a new subcategory under its tracker', async () => {
    await renderAt(`/personal/tracker/${EXPENSES_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a subcategory' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Transport');
    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));
    await screen.findByRole('button', { name: 'Transport' });

    expect(tables.categories).toEqual([
      expect.objectContaining({ name: 'Transport', parent_id: EXPENSES_ID, accrual: 'monthly' }),
    ]);
  });

  it('adds pots to One-offs, accruing across months', async () => {
    await renderAt(`/personal/tracker/${ONE_OFFS_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Add a pot' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Bike');
    await fireEvent.changeText(screen.getByLabelText('Cost'), '600');
    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));
    await screen.findByRole('button', { name: 'Bike' });

    expect(tables.categories).toEqual([
      expect.objectContaining({ name: 'Bike', cost: 600, accrual: 'multi_month' }),
    ]);
  });

  it('changes the tracker’s budget', async () => {
    await renderAt(`/personal/tracker/${EXPENSES_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Change budget' }));
    await fireEvent.changeText(screen.getByLabelText('Monthly budget'), '1300');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByLabelText('£1,300.00 budget')).toBeOnTheScreen();
  });

  it('offers no subcategories on a tracker that is one pot', async () => {
    await renderAt(`/personal/tracker/${SAVINGS_ID}`);
    await screen.findByRole('button', { name: 'Change budget' });

    expect(screen.queryByRole('button', { name: 'Add a subcategory' })).not.toBeOnTheScreen();
  });
});

/** A stored expense booked to a category. */
function expense(id: string, name: string, amount: number, date: string, categoryId: string) {
  return {
    ...OWNED,
    id,
    name,
    payment_date: date,
    payment_type: 'expense',
    expense: amount,
    income: 0,
    checked: false,
    bank_account_id: '3c4d5e6f-0000-4000-8000-000000000001',
    category_id: categoryId,
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

describe('subcategory', () => {
  it('lists this month’s payments booked to it', async () => {
    tables.payments = [
      expense('4d5e6f70-0000-4000-8000-000000000001', 'Tesco', 46.2, today(), GROCERIES_ID),
      expense('4d5e6f70-0000-4000-8000-000000000002', 'Aldi', 30, '2020-01-15', GROCERIES_ID),
      expense('4d5e6f70-0000-4000-8000-000000000003', 'Bus', 2, today(), EXPENSES_ID),
    ];
    await renderAt(`/personal/category/${GROCERIES_ID}`);
    await screen.findByText('Tesco');

    expect(screen.queryByText('Aldi')).not.toBeOnTheScreen();
  });

  it('is opened from its tracker', async () => {
    await renderAt(`/personal/tracker/${EXPENSES_ID}`);

    await fireEvent.press(await screen.findByRole('button', { name: 'Groceries' }));

    expect(await screen.findByText('No payments this month.')).toBeOnTheScreen();
  });

  it('is edited from its own screen', async () => {
    await renderAt(`/personal/category/${GROCERIES_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Edit' }));
    await fireEvent.changeText(screen.getByLabelText('Monthly budget'), '450');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByLabelText('£450.00 budget')).toBeOnTheScreen();
  });

  it('is deleted once confirmed', async () => {
    await renderAt(`/personal/category/${GROCERIES_ID}`);
    await fireEvent.press(await screen.findByRole('button', { name: 'Edit' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByText(/No subcategories yet/)).toBeOnTheScreen();
  });
});

describe('pots', () => {
  it('shows a pot saved beyond its cost as saved, not overspent', async () => {
    tables.categories_view?.push({
      ...viewRow({
        ...OWNED,
        id: '1a2b3c4d-0000-4000-8000-000000000005',
        name: 'Trainers',
        parent_id: ONE_OFFS_ID,
        accrual: 'multi_month',
        budget: 0,
        cost: 100,
      }),
      accrued: 120,
      remaining: -20,
      progress: 120,
    });

    await renderAt(`/personal/tracker/${ONE_OFFS_ID}`);

    expect(await screen.findByText('Saved, £20.00 extra')).toBeOnTheScreen();
  });
});
