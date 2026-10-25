import type { SupabaseClient } from '@supabase/supabase-js';

import { GatewayError, PAGE_SIZE, supabaseGateway } from '@/data/gateway';

type Result = { data: unknown; error: { message: string } | null };

/**
 * A stand-in for supabase-js's query builder over one table of `total` rows:
 * records each select's filters and range, and answers with that slice.
 */
function fakeClient(total: number, error: { message: string } | null = null) {
  const requests: { eq: [string, string][]; range: [number, number] }[] = [];
  const client = {
    from: () => ({
      select: () => {
        const eq: [string, string][] = [];
        const builder = {
          eq: (column: string, value: string) => {
            eq.push([column, value]);
            return builder;
          },
          order: () => builder,
          range: (from: number, to: number): PromiseLike<Result> => {
            requests.push({ eq, range: [from, to] });
            const data = Array.from(
              { length: Math.max(0, Math.min(to + 1, total) - from) },
              (_, i) => ({
                id: String(from + i),
              }),
            );
            return Promise.resolve({ data: error ? null : data, error });
          },
        };
        return builder;
      },
    }),
  };
  return { client: client as unknown as SupabaseClient, requests };
}

describe('select', () => {
  it('pages until a short page', async () => {
    const { client } = fakeClient(PAGE_SIZE * 2 + 5);

    const rows = await supabaseGateway(client).select('payments', {});

    expect(rows).toHaveLength(PAGE_SIZE * 2 + 5);
  });

  it('asks for each page by range', async () => {
    const { client, requests } = fakeClient(PAGE_SIZE + 1);

    await supabaseGateway(client).select('payments', {});

    expect(requests.map((request) => request.range)).toEqual([
      [0, PAGE_SIZE - 1],
      [PAGE_SIZE, PAGE_SIZE * 2 - 1],
    ]);
  });

  it('applies every equality filter', async () => {
    const { client, requests } = fakeClient(1);

    await supabaseGateway(client).select('payments', { ownership_type: 'joint' });

    expect(requests[0]?.eq).toEqual([['ownership_type', 'joint']]);
  });

  it('raises a GatewayError for an API error', async () => {
    const { client } = fakeClient(1, { message: 'permission denied' });

    await expect(supabaseGateway(client).select('payments', {})).rejects.toBeInstanceOf(
      GatewayError,
    );
  });
});
