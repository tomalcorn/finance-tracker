import { QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useMemo } from 'react';

import { useServices } from '@/composition/ServicesProvider';
import { RepositoriesContext } from '@/hooks/repositories';

/** Provide the signed-in user's repositories, and the query cache used by their reads. */
export function DataProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const services = useServices();
  const repositories = useMemo(() => services.repositories(userId), [services, userId]);

  return (
    <QueryClientProvider client={services.queryClient}>
      <RepositoriesContext.Provider value={repositories}>{children}</RepositoriesContext.Provider>
    </QueryClientProvider>
  );
}
