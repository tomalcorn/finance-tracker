import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { createContext, useContext } from 'react';

import type { OwnershipType } from '@/domain/entities';
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

/** How long a reconciliation or setup holds, rechecked when the app next comes back into focus after. */
const RECONCILED_FOR_MS = 60 * 60 * 1000;

/**
 * Reconcile both halves' subscriptions, at most once an hour however many screens ask. Without a
 * joint account the joint half has nothing to do.
 */
function reconciliationOptions(repositories: Repositories) {
  return {
    queryKey: [repositories.userId, 'reconciliation'],
    queryFn: async () => {
      await repositories.reconcileSubscriptions('personal');
      await repositories.reconcileSubscriptions('joint');
      return null;
    },
    staleTime: RECONCILED_FOR_MS,
  };
}

/**
 * Set up one half's workspace, at most once an hour however many screens ask. Each half has its own
 * query, so a failure on the joint side can't block the personal one.
 */
function workspaceSetupOptions(repositories: Repositories, ownership: OwnershipType) {
  return {
    queryKey: [repositories.userId, 'workspaceSetup', ownership],
    queryFn: async () => {
      await repositories.initialiseWorkspace(ownership);
      return null;
    },
    staleTime: RECONCILED_FOR_MS,
  };
}

/** The outcome of setting up one half's workspace, for a screen to show if it failed. */
export function useWorkspaceSetup(ownership: OwnershipType): UseQueryResult<null> {
  return useQuery(workspaceSetupOptions(useRepositories(), ownership));
}

/** Keep both halves set up, without re-rendering when that finishes. */
export function useKeepWorkspaceSetUp(): void {
  const repositories = useRepositories();
  useQuery({ ...workspaceSetupOptions(repositories, 'personal'), notifyOnChangeProps: [] });
  useQuery({ ...workspaceSetupOptions(repositories, 'joint'), notifyOnChangeProps: [] });
}

/** The outcome of reconciling subscriptions, for a screen to show if it failed. */
export function useReconciliation(): UseQueryResult<null> {
  return useQuery(reconciliationOptions(useRepositories()));
}

/** Keep subscriptions reconciled, without re-rendering when that finishes. */
export function useKeepReconciled(): void {
  useQuery({ ...reconciliationOptions(useRepositories()), notifyOnChangeProps: [] });
}

/** A repository's rows, cached, and fetched again whenever made out of date by a write. */
export function useRows<ViewT>(repository: Repository<object, ViewT>): UseQueryResult<ViewT[]> {
  return useQuery({ queryKey: repository.cacheKey, queryFn: () => repository.rows() });
}
