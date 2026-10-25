import type { CacheInvalidator } from '@/data/cache';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import type { ReadSource } from '@/data/tables';
import { InvalidRowError, NoJointAccountError, RepositoryError } from '@/ports/errors';
import type { CacheKey } from '@/ports/repository';

const USER_ID = 'auth0|65f0c2a1b3d4e5f6a7b8c9d0';
const JOINT_ID = '9a3d6e1f-4c2b-4f7a-8e5d-1b6c3a9f2e08';
const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';
const BUTTON_ID = '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01';

const STORED_BUTTON: StoredRow = {
  id: BUTTON_ID,
  user_id: USER_ID,
  name: 'Coffee',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  mode: 'log',
  payment_name: null,
  expense: 3.2,
  bank_account_id: BANK_ACCOUNT_ID,
  category_id: null,
  icon: '☕',
  display_order: 0,
};

/** An in-memory gateway: `select` filters `tables` by equality and records every call. */
class FakeGateway implements TableGateway {
  readonly calls: { method: string; source: string; arg: unknown }[] = [];
  failWith: Error | null = null;

  constructor(readonly tables: Partial<Record<ReadSource, StoredRow[]>> = {}) {}

  async select(source: ReadSource, eq: Readonly<Record<string, string>>) {
    this.calls.push({ method: 'select', source, arg: eq });
    if (this.failWith) throw this.failWith;
    return (this.tables[source] ?? []).filter((row) =>
      Object.entries(eq).every(([column, value]) => row[column] === value),
    );
  }

  async upsert(source: ReadSource, rows: readonly object[]) {
    this.calls.push({ method: 'upsert', source, arg: rows });
    if (this.failWith) throw this.failWith;
  }

  async delete(source: ReadSource, ids: readonly string[]) {
    this.calls.push({ method: 'delete', source, arg: ids });
    if (this.failWith) throw this.failWith;
  }
}

class RecordingCache implements CacheInvalidator {
  readonly invalidated: CacheKey[] = [];

  async invalidate(keys: readonly CacheKey[]) {
    this.invalidated.push(...keys);
  }
}

let gateway: FakeGateway;
let cache: RecordingCache;

function repositories() {
  return createRepositories({ userId: USER_ID, gateway, cache });
}

beforeEach(() => {
  gateway = new FakeGateway({
    quick_buttons: [
      STORED_BUTTON,
      {
        ...STORED_BUTTON,
        id: BANK_ACCOUNT_ID,
        ownership_type: 'joint',
        joint_account_id: JOINT_ID,
      },
    ],
    joint_accounts: [{ id: JOINT_ID, name: 'Household' }],
  });
  cache = new RecordingCache();
});

describe('rows', () => {
  it("read only the repository's half", async () => {
    const rows = await repositories().quickButtons('personal').rows();

    expect(rows.map((row) => row.id)).toEqual([BUTTON_ID]);
  });

  it('parse stored rows into view rows', async () => {
    const [row] = await repositories().quickButtons('personal').rows();

    expect(row).toEqual(STORED_BUTTON);
  });

  it('reject a malformed stored row, naming where it came from', async () => {
    gateway.tables.quick_buttons = [{ ...STORED_BUTTON, display_order: 'first' }];

    await expect(repositories().quickButtons('personal').rows()).rejects.toMatchObject({
      constructor: InvalidRowError,
      table: 'quick_buttons',
      issues: [expect.objectContaining({ field: 'display_order' })],
    });
  });

  it('need a joint account to read the joint half', async () => {
    gateway.tables.joint_accounts = [];

    await expect(repositories().quickButtons('joint').rows()).rejects.toMatchObject({
      constructor: NoJointAccountError,
      userId: USER_ID,
    });
  });
});

describe('build', () => {
  it('stamps the owner and ownership over whatever the row claims', async () => {
    const [button] = await repositories()
      .quickButtons('personal')
      .build([
        {
          name: 'Coffee',
          mode: 'prompt',
          user_id: 'someone-else',
          ownership_type: 'joint',
          joint_account_id: JOINT_ID,
        },
      ]);

    expect(button).toMatchObject({
      user_id: USER_ID,
      ownership_type: 'personal',
      joint_account_id: null,
    });
  });

  it("files a joint row under the user's joint account", async () => {
    const [button] = await repositories()
      .quickButtons('joint')
      .build([{ name: 'Coffee', mode: 'prompt' }]);

    expect(button?.joint_account_id).toBe(JOINT_ID);
  });

  it('turns a view row back into an entity, dropping the read-only columns', async () => {
    const [button] = await repositories()
      .quickButtons('personal')
      .build([{ ...STORED_BUTTON, name: 'Flat white' }]);

    expect(button).not.toHaveProperty('_created_at');
  });

  it('rejects a row that breaks its rules, naming the field', async () => {
    await expect(
      repositories()
        .quickButtons('personal')
        .build([{ name: 'Coffee', mode: 'log' }]),
    ).rejects.toMatchObject({
      constructor: InvalidRowError,
      table: 'quick_buttons',
      issues: [
        expect.objectContaining({ field: 'expense' }),
        expect.objectContaining({ field: 'bank_account_id' }),
      ],
    });
  });

  it('fills a joint-table row with no ownership columns', async () => {
    const [member] = await repositories()
      .jointAccountMembers()
      .build([{ joint_account_id: JOINT_ID }]);

    expect(member).toEqual({
      id: expect.any(String),
      joint_account_id: JOINT_ID,
      user_id: USER_ID,
    });
  });
});

describe('save', () => {
  it('upserts the entities', async () => {
    const repo = repositories().quickButtons('personal');
    const entities = await repo.build([{ name: 'Coffee', mode: 'prompt' }]);

    await repo.save(entities);

    expect(gateway.calls.at(-1)).toEqual({
      method: 'upsert',
      source: 'quick_buttons',
      arg: entities,
    });
  });

  it('refuses an entity owned by the other half', async () => {
    const repos = repositories();
    const personal = await repos
      .quickButtons('personal')
      .build([{ name: 'Coffee', mode: 'prompt' }]);

    await expect(repos.quickButtons('joint').save(personal)).rejects.toBeInstanceOf(
      RepositoryError,
    );
  });

  it("invalidates the table's own key", async () => {
    const repo = repositories().quickButtons('personal');

    await repo.save(await repo.build([{ name: 'Coffee', mode: 'prompt' }]));

    expect(cache.invalidated).toEqual([[USER_ID, 'personal', 'quick_buttons']]);
  });

  it('invalidates every view a payment is summed into', async () => {
    const repo = repositories().payments('personal');

    await repo.save(
      await repo.build([{ payment_type: 'expense', bank_account_id: BANK_ACCOUNT_ID }]),
    );

    expect(cache.invalidated).toEqual([
      [USER_ID, 'personal', 'payments'],
      [USER_ID, 'personal', 'bank_accounts_view'],
      [USER_ID, 'personal', 'categories_view'],
      [USER_ID, 'personal', 'income_sources_view'],
    ]);
  });

  it('does nothing for no entities', async () => {
    await repositories().quickButtons('personal').save([]);

    expect(gateway.calls).toEqual([]);
  });
});

describe('delete', () => {
  it('deletes by id', async () => {
    await repositories().quickButtons('personal').delete([BUTTON_ID]);

    expect(gateway.calls.at(-1)).toEqual({
      method: 'delete',
      source: 'quick_buttons',
      arg: [BUTTON_ID],
    });
  });

  it('invalidates the joint payments a personal subscription cascades to', async () => {
    await repositories().subscriptions('personal').delete([BUTTON_ID]);

    expect(cache.invalidated).toContainEqual([USER_ID, 'joint', 'payments']);
  });
});

describe('failures', () => {
  it('translate a gateway failure into a RepositoryError', async () => {
    gateway.failWith = new GatewayError('Reading quick_buttons failed: timeout');

    await expect(repositories().quickButtons('personal').rows()).rejects.toMatchObject({
      constructor: RepositoryError,
      cause: gateway.failWith,
    });
  });

  it('let any other error through untouched', async () => {
    gateway.failWith = new TypeError('a bug');

    await expect(repositories().quickButtons('personal').rows()).rejects.toBe(gateway.failWith);
  });
});

describe('createRepositories', () => {
  it('returns the same repository for the same half', () => {
    const repos = repositories();

    expect(repos.quickButtons('joint')).toBe(repos.quickButtons('joint'));
  });

  it('reads the joint account once for every joint repository', async () => {
    const repos = repositories();

    await repos.quickButtons('joint').rows();
    await repos.payments('joint').rows();

    expect(gateway.calls.filter((call) => call.source === 'joint_accounts')).toHaveLength(1);
  });

  it('reads the joint account again after a failed read', async () => {
    const repos = repositories();
    gateway.failWith = new GatewayError('offline');
    await repos
      .quickButtons('joint')
      .rows()
      .catch(() => {});
    gateway.failWith = null;

    await expect(repos.quickButtons('joint').rows()).resolves.toHaveLength(1);
  });
});
