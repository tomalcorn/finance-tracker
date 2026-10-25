import type { z } from 'zod';

import type { CacheInvalidator } from '@/data/cache';
import { GatewayError, type StoredRow, type TableGateway } from '@/data/gateway';
import { AFFECTED_BY, CASCADES_TO_JOINT, type ReadSource, type TableName } from '@/data/tables';
import type { OwnershipType, RawRow } from '@/domain/entities';
import { InvalidRowError, NoJointAccountError, RepositoryError } from '@/ports/errors';
import type { CacheKey, Repository } from '@/ports/repository';

/** The per-aggregate configuration a repository is built from. */
export type RepoSpec<EntityT extends object, ViewT> = {
  entity: z.ZodType<EntityT>;
  view: z.ZodType<ViewT>;
  readFrom: ReadSource;
  writeTo: TableName;
};

/** What a repository is bound to: the user, the ownership mode, and its dependencies. */
export type RepoContext = {
  userId: string;
  /** `null` for the joint tables, which have no ownership dimension. */
  ownership: OwnershipType | null;
  gateway: TableGateway;
  cache: CacheInvalidator;
  /** The user's joint account id, or `null` when they belong to none. */
  jointAccountId: () => Promise<string | null>;
};

/** The cache key for `source` under one user and ownership mode. */
export function cacheKey(
  userId: string,
  ownership: OwnershipType | null,
  source: ReadSource,
): CacheKey {
  return [userId, ownership ?? 'unowned', source];
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
    const id = await translate('Finding the joint account', context.jointAccountId);
    if (id === null) throw new NoJointAccountError(userId);
    return id;
  }

  /** The ownership columns every row this repository writes carries. */
  async function ownershipFields(): Promise<Record<string, string | null>> {
    if (ownership === null) return {};
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

  /** Every key a write to this table changes. */
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
    if (ownership === null) return;
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
      const eq: Record<string, string> = ownership === null ? {} : { ownership_type: ownership };
      if (ownership === 'joint') await jointAccountId();
      const stored = await translate(`Reading ${spec.readFrom}`, () =>
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
      await translate(`Writing ${spec.writeTo}`, () => gateway.upsert(spec.writeTo, items));
      await cache.invalidate(affectedKeys());
    },

    async delete(ids) {
      if (ids.length === 0) return;
      await translate(`Deleting from ${spec.writeTo}`, () => gateway.delete(spec.writeTo, ids));
      await cache.invalidate(affectedKeys());
    },
  };
}

/** Run a gateway call, translating only its own failure into a `RepositoryError`. */
async function translate<T>(action: string, call: () => Promise<T>): Promise<T> {
  try {
    return await call();
  } catch (error) {
    if (error instanceof GatewayError) {
      throw new RepositoryError(`${action} failed: ${error.message}`, { cause: error });
    }
    throw error;
  }
}
