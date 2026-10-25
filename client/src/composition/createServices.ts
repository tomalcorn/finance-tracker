import { QueryClient } from '@tanstack/react-query';

import type { AuthClient } from '@/auth/authClient';
import { createAuthClient } from '@/auth/createAuthClient';
import { queryCache } from '@/composition/queryCache';
import { loadConfig } from '@/config';
import { supabaseGateway } from '@/data/gateway';
import { createRepositories } from '@/data/repositories';
import { createSupabase } from '@/data/supabase';
import { InvalidRowError, NoJointAccountError } from '@/ports/errors';
import type { Repositories } from '@/ports/repositories';

/** The app's outbound dependencies, built once per page load. */
export type Services = {
  auth: AuthClient;
  /** Caches every read made by screens. */
  queryClient: QueryClient;
  /** The signed-in user's repositories: the same object on every call for the same user. */
  repositories(userId: string): Repositories;
};

/** Retry a failed read unless it would only fail the same way again. */
function shouldRetry(failureCount: number, error: Error): boolean {
  return (
    !(error instanceof InvalidRowError || error instanceof NoJointAccountError) && failureCount < 3
  );
}

/**
 * Build the real services from the bundled configuration.
 *
 * @throws {ConfigError} when the configuration is incomplete.
 */
export function createServices(): Services {
  const config = loadConfig();
  const auth = createAuthClient(config);
  const gateway = supabaseGateway(createSupabase(config, () => auth.getIdToken()));
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } });
  const cache = queryCache(queryClient);
  const repositoriesByUser = new Map<string, Repositories>();
  return {
    auth,
    queryClient,
    repositories(userId) {
      let repositories = repositoriesByUser.get(userId);
      if (!repositories) {
        repositories = createRepositories({ userId, gateway, cache });
        repositoriesByUser.set(userId, repositories);
      }
      return repositories;
    },
  };
}
