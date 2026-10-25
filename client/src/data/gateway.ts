import type { SupabaseClient } from '@supabase/supabase-js';

import type { ReadSource, TableName } from '@/data/tables';

/** A stored row as the database returns it, before any schema has read it. */
export type StoredRow = Record<string, unknown>;

/**
 * The table operations a repository needs. Internal to `src/data/`: callers
 * outside it go through a `Repository`.
 */
export interface TableGateway {
  /** Every row of `source` matching each `column = value` in `eq`. */
  select(source: ReadSource, eq: Readonly<Record<string, string>>): Promise<StoredRow[]>;

  /** Insert each row, or update it in place when its id exists. */
  upsert(table: TableName, rows: readonly object[]): Promise<void>;

  delete(table: TableName, ids: readonly string[]): Promise<void>;
}

/** A gateway request failed. Translated into a `RepositoryError` by the repository. */
export class GatewayError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = 'GatewayError';
  }
}

/** The most rows a select fetches per request; Supabase caps a response at 1,000. */
export const PAGE_SIZE = 1000;

/** The gateway over supabase-js, paging every select so none is cut short. */
export function supabaseGateway(client: SupabaseClient): TableGateway {
  async function run<T>(
    action: string,
    request: PromiseLike<{ data: T; error: { message: string } | null }>,
  ): Promise<T> {
    let result;
    try {
      result = await request;
    } catch (error) {
      throw new GatewayError(`${action} failed: ${String(error)}`, { cause: error });
    }
    if (result.error) {
      throw new GatewayError(`${action} failed: ${result.error.message}`, { cause: result.error });
    }
    return result.data;
  }

  return {
    async select(source, eq) {
      const rows: StoredRow[] = [];
      for (let from = 0; ; from += PAGE_SIZE) {
        let query = client.from(source).select('*');
        for (const [column, value] of Object.entries(eq)) {
          query = query.eq(column, value);
        }
        const page = await run<StoredRow[] | null>(
          `Reading ${source}`,
          query.order('id').range(from, from + PAGE_SIZE - 1),
        );
        rows.push(...(page ?? []));
        if (!page || page.length < PAGE_SIZE) return rows;
      }
    },

    async upsert(table, rows) {
      await run(`Writing ${table}`, client.from(table).upsert([...rows]));
    },

    async delete(table, ids) {
      await run(
        `Deleting from ${table}`,
        client
          .from(table)
          .delete()
          .in('id', [...ids]),
      );
    },
  };
}
