import { QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useMemo } from 'react';

import { useServices } from '@/composition/ServicesProvider';
import {
  RepositoriesContext,
  useKeepReconciled,
  useKeepWorkspaceSetUp,
} from '@/hooks/repositories';

/**
 * As soon as the app opens, on whichever screen, give a new user their workspace and book the
 * subscription payments now due.
 */
function PrepareOnOpen() {
  useKeepWorkspaceSetUp();
  useKeepReconciled();
  return null;
}

/** Provide the signed-in user's repositories, and the query cache used by their reads. */
export function DataProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const services = useServices();
  const repositories = useMemo(() => services.repositories(userId), [services, userId]);

  return (
    <QueryClientProvider client={services.queryClient}>
      <RepositoriesContext.Provider value={repositories}>
        <PrepareOnOpen />
        {children}
      </RepositoriesContext.Provider>
    </QueryClientProvider>
  );
}
