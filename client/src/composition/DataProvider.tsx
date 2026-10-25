import { QueryClientProvider, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { createContext, type ReactNode, useContext, useMemo } from 'react';

import { useServices } from '@/composition/ServicesProvider';
import type { Repositories } from '@/ports/repositories';
import type { Repository } from '@/ports/repository';

const RepositoriesContext = createContext<Repositories | null>(null);

/** Provide the signed-in user's repositories, and the query cache their reads go through. */
export function DataProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const services = useServices();
  const repositories = useMemo(() => services.repositories(userId), [services, userId]);

  return (
    <QueryClientProvider client={services.queryClient}>
      <RepositoriesContext.Provider value={repositories}>{children}</RepositoriesContext.Provider>
    </QueryClientProvider>
  );
}

/**
 * The signed-in user's repositories.
 *
 * @throws {Error} when called outside a `DataProvider`.
 */
export function useRepositories(): Repositories {
  const repositories = useContext(RepositoriesContext);
  if (!repositories) {
    throw new Error('useRepositories must be used inside a DataProvider.');
  }
  return repositories;
}

/** A repository's rows, cached, and refetched whenever a write invalidates them. */
export function useRows<ViewT>(repository: Repository<object, ViewT>): UseQueryResult<ViewT[]> {
  return useQuery({ queryKey: repository.cacheKey, queryFn: () => repository.rows() });
}
