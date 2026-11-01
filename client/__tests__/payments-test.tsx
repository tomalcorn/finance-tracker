import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen, within } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import { queryCache } from '@/composition/queryCache';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import type { StoredRow, TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { today } from '@/domain/entities';
import { monthOf, shiftMonth } from '@/payments/paymentList';

const APP_DIR = './src/app';
const USER_ID = 'auth0|test';
const CREATED_AT = '2026-10-01T09:30:12.345678+00:00';
const BANK_ID = '3c4d5e6f-0000-4000-8000-000000000001';
const GROCERIES_ID = '1a2b3c4d-0000-4000-8000-000000000004';
const SALARY_SOURCE_ID = '2b3c4d5e-0000-4000-8000-000000000001';
const COFFEE_ID = '4d5e6f70-0000-4000-8000-000000000001';
const SALARY_ID = '4d5e6f70-0000-4000-8000-000000000002';
const RENT_ID = '4d5e6f70-0000-4000-8000-000000000003';

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

/** A stored payment: an expense unless `income` is given. */
function payment(id: string, name: string, date: string, amount: number, income = false) {
  return {
    ...OWNED,
    id,
    name,
    payment_date: date,
    payment_type: income ? 'income' : 'expense',
    expense: income ? 0 : amount,
    income: income ? amount : 0,
    checked: false,
    bank_account_id: BANK_ID,
    category_id: income ? null : GROCERIES_ID,
    income_source_id: income ? SALARY_SOURCE_ID : null,
    subscription_id: null,
    linked_payment_id: null,
  };
}

/**
 * A database in memory. A new row is stamped as added after every row before it; an updated row
 * keeps its stamp. A payment carries both kinds' source columns, null where unused, as the table's
 * do.
 */
function memoryGateway(tables: Record<string, StoredRow[]>): TableGateway {
  let added = 0;
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
        const createdAt =
          index === -1
            ? `2026-12-01T00:00:${String(++added).padStart(2, '0')}+00:00`
            : stored[index]?._created_at;
        const columns = table === 'payments' ? { category_id: null, income_source_id: null } : {};
        stored.splice(index === -1 ? stored.length : index, 1, {
          ...columns,
          ...row,
          _created_at: createdAt,
        });
      }
      tables[table] = stored;
    },
    async delete(table, ids) {
      tables[table] = (tables[table] ?? []).filter((row) => !ids.includes(row.id as string));
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

const lastMonth = `${shiftMonth(monthOf(today()), -1)}-28`;

beforeEach(() => {
  tables = {
    payments: [
      payment(COFFEE_ID, 'Coffee', today(), 3.4),
      payment(SALARY_ID, 'Salary', today(), 2500, true),
      payment(RENT_ID, 'Rent', lastMonth, 900),
    ],
    bank_accounts_view: [
      { ...OWNED, id: BANK_ID, name: 'Monzo', starting_balance: 0, current_balance: 0 },
    ],
    categories_view: [
      {
        ...OWNED,
        id: GROCERIES_ID,
        name: 'Groceries',
        parent_id: null,
        accrual: 'monthly',
        budget: 400,
        cost: 0,
        starting_balance: 0,
        accrued: 0,
        remaining: 400,
        progress: 0,
        split: 0,
      },
    ],
    income_sources_view: [
      {
        ...OWNED,
        id: SALARY_SOURCE_ID,
        name: 'Salary',
        budget_tracker_ids: [],
        current_month: 2500,
        income_roll_up_period: 'current_month',
      },
    ],
  };
});

/** The stored payment with this id. */
function stored(id: string) {
  return tables.payments?.find((row) => row.id === id);
}

describe('payments overview', () => {
  it('shows what went out this month', async () => {
    await renderAt('/personal');

    expect(await screen.findByText(/^£3\.40 out in/)).toBeOnTheScreen();
  });

  it('opens the payments', async () => {
    await renderAt('/personal');

    await fireEvent.press(await screen.findByRole('button', { name: 'Payments' }));

    expect(await screen.findByRole('button', { name: 'Coffee' })).toBeOnTheScreen();
  });
});

describe('payments list', () => {
  it('shows money out as negative', async () => {
    await renderAt('/personal/payments');

    expect(await screen.findByText('-£3.40')).toBeOnTheScreen();
  });

  it('describes a payment by its category and account', async () => {
    await renderAt('/personal/payments');

    expect(await screen.findByText('Groceries · Monzo')).toBeOnTheScreen();
  });

  it('leaves out other months', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });

    expect(screen.queryByRole('button', { name: 'Rent' })).not.toBeOnTheScreen();
  });

  it('steps back a month', async () => {
    await renderAt('/personal/payments');

    await fireEvent.press(await screen.findByRole('button', { name: 'Previous month' }));

    expect(await screen.findByRole('button', { name: 'Rent' })).toBeOnTheScreen();
  });

  it('shows only money in when asked', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });

    await fireEvent.press(screen.getByRole('radio', { name: 'In' }));

    expect(screen.queryByRole('button', { name: 'Coffee' })).not.toBeOnTheScreen();
  });

  it('narrows to what is searched for', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });

    await fireEvent.changeText(screen.getByLabelText('Search'), 'sal');

    expect(screen.queryByRole('button', { name: 'Coffee' })).not.toBeOnTheScreen();
  });

  it('ticks a payment as checked from the list', async () => {
    await renderAt('/personal/payments');

    await fireEvent.press(await screen.findByRole('checkbox', { name: 'Coffee checked' }));

    expect(stored(COFFEE_ID)).toEqual(expect.objectContaining({ checked: true }));
  });
});

describe('spending by category', () => {
  it('groups money out by category', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });

    await fireEvent.press(screen.getByRole('radio', { name: 'By category' }));

    expect(screen.getByText('1 payment · 100% of spending')).toBeOnTheScreen();
  });

  it('leaves money in out', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });

    await fireEvent.press(screen.getByRole('radio', { name: 'By category' }));

    expect(screen.queryByRole('button', { name: 'Salary' })).not.toBeOnTheScreen();
  });

  it('opens a category to its payments', async () => {
    await renderAt('/personal/payments');
    await screen.findByRole('button', { name: 'Coffee' });
    await fireEvent.press(screen.getByRole('radio', { name: 'By category' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Groceries' }));

    expect(screen.getByRole('button', { name: 'Coffee' })).toBeOnTheScreen();
  });
});

describe('adding a payment', () => {
  async function addExpense(name: string, amount: string) {
    await fireEvent.press(await screen.findByRole('button', { name: 'Add' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), name);
    await fireEvent.changeText(screen.getByLabelText('Amount out'), amount);
    await fireEvent.press(screen.getByRole('button', { name: 'Add payment' }));
  }

  it('saves an expense, today, from the only account', async () => {
    await renderAt('/personal/payments');

    await addExpense('Lunch', '8.50');
    await screen.findByText('Lunch added');

    expect(tables.payments?.at(-1)).toEqual(
      expect.objectContaining({
        name: 'Lunch',
        payment_type: 'expense',
        expense: 8.5,
        payment_date: today(),
        bank_account_id: BANK_ID,
      }),
    );
  });

  it('puts the new payment at the top of its day', async () => {
    await renderAt('/personal/payments');

    await addExpense('Lunch', '8.50');
    await screen.findByText('Lunch added');

    const rows = screen.getAllByRole('button', { name: /^(Lunch|Coffee|Salary)$/ });
    expect(rows.map((row) => row.props.accessibilityLabel)).toEqual(['Lunch', 'Coffee', 'Salary']);
  });

  it('saves money in against an income source', async () => {
    await renderAt('/personal/payments');
    await fireEvent.press(await screen.findByRole('button', { name: 'Add' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Money in' }));
    await fireEvent.changeText(screen.getByLabelText('Name'), 'Bonus');
    await fireEvent.changeText(screen.getByLabelText('Amount in'), '300');

    await fireEvent.press(screen.getByRole('button', { name: 'Add payment' }));
    await screen.findByText('Bonus added');

    expect(tables.payments?.at(-1)).toEqual(
      expect.objectContaining({ payment_type: 'income', income: 300, expense: 0 }),
    );
  });

  it('says what is missing', async () => {
    await renderAt('/personal/payments');
    await fireEvent.press(await screen.findByRole('button', { name: 'Add' }));

    await fireEvent.press(screen.getByRole('button', { name: 'Add payment' }));

    expect(screen.getByText('Give it a name.')).toBeOnTheScreen();
  });
});

describe('editing a payment', () => {
  it('saves a change', async () => {
    await renderAt('/personal/payments');
    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));
    await fireEvent.changeText(screen.getByLabelText('Amount out'), '3.80');

    await fireEvent.press(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByText('-£3.80')).toBeOnTheScreen();
  });

  it('keeps an existing payment’s kind', async () => {
    await renderAt('/personal/payments');

    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));

    expect(screen.queryByRole('radio', { name: 'Money in' })).not.toBeOnTheScreen();
  });

  it('deletes it once confirmed', async () => {
    await renderAt('/personal/payments');
    await fireEvent.press(await screen.findByRole('button', { name: 'Coffee' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Delete' }));

    await fireEvent.press(
      within(screen.getByText('Delete “Coffee”?').parent!.parent!).getByRole('button', {
        name: 'Delete',
      }),
    );
    await screen.findByText('Coffee deleted');

    expect(stored(COFFEE_ID)).toBeUndefined();
  });
});
