import { createContext, type ReactNode, useContext, useState, useSyncExternalStore } from 'react';

import { AuthProvider } from '@/auth/AuthProvider';
import { createServices, type Services } from '@/composition/createServices';

/** Services once built, or why they could not be. Both null while building. */
export type ServicesState = {
  services: Services | null;
  error: Error | null;
};

const NOT_BUILT: ServicesState = { services: null, error: null };

const ServicesContext = createContext<ServicesState>(NOT_BUILT);

const ServicesFactoryContext = createContext<() => Services>(createServices);

/**
 * Make every `ServicesProvider` below build its services with `create`.
 *
 * Without one, `ServicesProvider` uses the real `createServices`. Tests wrap
 * the router in this to supply fakes, since the root layout takes no props.
 */
export function ServicesFactoryProvider({
  create,
  children,
}: {
  create: () => Services;
  children: ReactNode;
}) {
  return (
    <ServicesFactoryContext.Provider value={create}>{children}</ServicesFactoryContext.Provider>
  );
}

function build(create: () => Services): ServicesState {
  try {
    return { services: create(), error: null };
  } catch (error) {
    return { services: null, error: error instanceof Error ? error : new Error(String(error)) };
  }
}

const neverChanges = () => () => {};

/**
 * Build the services in the browser and provide them below, along with the
 * session (`useAuth`) resolved through their auth client.
 *
 * They are never built while rendering on the server: the static web export
 * renders every route in Node, where there is no `window` for the Auth0 SDK.
 * The server snapshot is "not built", which is also what the browser's first
 * (hydrating) render sees, so consumers show a loading state until then.
 */
export function ServicesProvider({ children }: { children: ReactNode }) {
  const create = useContext(ServicesFactoryContext);
  const [getBuilt] = useState(() => {
    let built: ServicesState | undefined;
    return () => (built ??= build(create));
  });
  const state = useSyncExternalStore(neverChanges, getBuilt, () => NOT_BUILT);

  return (
    <ServicesContext.Provider value={state}>
      <AuthProvider auth={state.services?.auth ?? null} unavailable={state.error}>
        {children}
      </AuthProvider>
    </ServicesContext.Provider>
  );
}

/**
 * The built services, for components that only render once signed in.
 *
 * @throws {Error} when called before the services exist.
 */
export function useServices(): Services {
  const { services } = useContext(ServicesContext);
  if (!services) {
    throw new Error('useServices was called before the services were built.');
  }
  return services;
}
