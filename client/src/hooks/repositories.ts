import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { createContext, useContext } from 'react';

import { MissingProviderError } from '@/hooks/MissingProviderError';
import type { Repositories } from '@/ports/repositories';
import type { Repository } from '@/ports/repository';

/** Holds the signed-in user's repositories. Filled in by composition's `DataProvider`. */
export const RepositoriesContext = createContext<Repositories | null>(null);

/**
 * The signed-in user's repositories.
 *
 * @throws {MissingProviderError} when called outside a `DataProvider`.
 */
export function useRepositories(): Repositories {
  const repositories = useContext(RepositoriesContext);
  if (!repositories) {
    throw new MissingProviderError('useRepositories', 'DataProvider');
  }
  return repositories;
}

/** A repository's rows, cached, and fetched again whenever made out of date by a write. */
export function useRows<ViewT>(repository: Repository<object, ViewT>): UseQueryResult<ViewT[]> {
  return useQuery({ queryKey: repository.cacheKey, queryFn: () => repository.rows() });
}
