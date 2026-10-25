import type { z } from 'zod';

import type { CacheInvalidator } from '@/data/cache';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { AFFECTED_BY, CASCADES_TO_JOINT, type ReadSource, type TableName } from '@/data/tables';
import type { OwnershipType, RawRow } from '@/domain/entities';
import { InvalidRowError, NoJointAccountError, RepositoryError } from '@/ports/errors';
import type { CacheKey, Repository } from '@/ports/repository';

/** The per-aggregate configuration used to build a repository. */
export type RepoSpec<EntityT extends object, ViewT> = {
  entity: z.ZodType<EntityT>;
  view: z.ZodType<ViewT>;
  readFrom: ReadSource;
  writeTo: TableName;
};

/**
 * The rows read and written by a repository: the user's personal ones, their
 * joint account's, or `unowned` for `joint_accounts` and
 * `joint_account_members`, which belong to neither half.
 */
export type RepoOwnership = OwnershipType | 'unowned';

/** What a repository is bound to: the user, the ownership mode, and its dependencies. */
export type RepoContext = {
  userId: string;
  ownership: RepoOwnership;
  gateway: TableGateway;
  cache: CacheInvalidator;
  /** The user's joint account id, or `null` when they belong to none. */
  jointAccountId: () => Promise<string | null>;
};

/** The cache key for `source` under one user and ownership mode. */
export function cacheKey(userId: string, ownership: RepoOwnership, source: ReadSource): CacheKey {
  return [userId, ownership, source];
}

function issuesOf(error: z.ZodError) {
  return error.issues.map((issue) => ({
    field: issue.path.join('.') || '(row)',
    message: issue.message,
  }));
}

/** Build a repository for one aggregate, in one ownership mode. */
export function createRepository<EntityT extends object, ViewT>(
  spec: RepoSpec<EntityT, ViewT>,
  context: RepoContext,
): Repository<EntityT, ViewT> {
  const { userId, ownership, gateway, cache } = context;

  async function jointAccountId(): Promise<string> {
    const id = await translateError('Finding the joint account', context.jointAccountId);
    if (id === null) throw new NoJointAccountError(userId);
    return id;
  }

  /** The ownership columns carried by every row written by this repository. */
  async function ownershipFields(): Promise<Record<string, string | null>> {
    if (ownership === 'unowned') return {};
    return {
      ownership_type: ownership,
      joint_account_id: ownership === 'joint' ? await jointAccountId() : null,
    };
  }

  function parse<T>(schema: z.ZodType<T>, row: unknown, table: string): T {
    const result = schema.safeParse(row);
    if (!result.success) {
      throw new InvalidRowError(table, issuesOf(result.error), { cause: result.error });
    }
    return result.data;
  }

  /** The cache keys made out of date by a write to this table. */
  function affectedKeys(): CacheKey[] {
    const own = [spec.writeTo, ...(AFFECTED_BY[spec.writeTo] ?? [])];
    const keys = own.map((source) => cacheKey(userId, ownership, source));
    if (ownership === 'personal') {
      for (const source of CASCADES_TO_JOINT[spec.writeTo] ?? []) {
        keys.push(cacheKey(userId, 'joint', source));
      }
    }
    return keys;
  }

  async function assertOwned(items: readonly EntityT[]): Promise<void> {
    if (ownership === 'unowned') return;
    const expected = await ownershipFields();
    const misfiled = items.some(
      (item) =>
        !('ownership_type' in item && 'joint_account_id' in item) ||
        item.ownership_type !== expected.ownership_type ||
        item.joint_account_id !== expected.joint_account_id,
    );
    if (misfiled) {
      throw new RepositoryError(
        `Cannot save to ${spec.writeTo}: an entity is not ${ownership}-owned by this repository.`,
      );
    }
  }

  return {
    cacheKey: cacheKey(userId, ownership, spec.readFrom),

    async rows() {
      const eq: Record<string, string> =
        ownership === 'unowned' ? {} : { ownership_type: ownership };
      if (ownership === 'joint') await jointAccountId();
      const stored = await translateError(`Reading ${spec.readFrom}`, () =>
        gateway.select(spec.readFrom, eq),
      );
      return stored.map((row: StoredRow) => parse(spec.view, row, spec.readFrom));
    },

    async build(rows: readonly RawRow[]) {
      const fields = { user_id: userId, ...(await ownershipFields()) };
      return rows.map((row) => parse(spec.entity, { ...row, ...fields }, spec.writeTo));
    },

    async save(items) {
      if (items.length === 0) return;
      await assertOwned(items);
      await translateError(`Writing ${spec.writeTo}`, () => gateway.upsert(spec.writeTo, items));
      await cache.invalidate(affectedKeys());
    },

    async delete(ids) {
      if (ids.length === 0) return;
      await translateError(`Deleting from ${spec.writeTo}`, () =>
        gateway.delete(spec.writeTo, ids),
      );
      await cache.invalidate(affectedKeys());
    },
  };
}

/**
 * Run a gateway call. If the gateway fails, rethrow its error as a
 * `RepositoryError`; let any other error through unchanged.
 */
async function translateError<T>(action: string, call: () => Promise<T>): Promise<T> {
  try {
    return await call();
  } catch (error) {
    if (error instanceof GatewayError) {
      throw new RepositoryError(`${action} failed: ${error.message}`, { cause: error });
    }
    throw error;
  }
}
