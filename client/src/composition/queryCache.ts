import type { QueryClient } from '@tanstack/react-query';

import type { CacheInvalidator } from '@/data/cache';

/** The repositories' cache, over TanStack Query: invalidating a key refetches any screen showing it. */
export function queryCache(queryClient: QueryClient): CacheInvalidator {
  return {
    async invalidate(keys) {
      await Promise.all(keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
    },
  };
}
