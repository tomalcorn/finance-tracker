import { createContext, type ReactNode, useContext, useState, useSyncExternalStore } from 'react';

import { createServices, type Services } from '@/composition/createServices';

/** Services once built, or why they could not be. Both null while building. */
export type ServicesState = {
  services: Services | null;
  error: Error | null;
};

const NOT_BUILT: ServicesState = { services: null, error: null };

const ServicesContext = createContext<ServicesState>(NOT_BUILT);

function build(): ServicesState {
  try {
    return { services: createServices(), error: null };
  } catch (error) {
    return { services: null, error: error instanceof Error ? error : new Error(String(error)) };
  }
}

const neverChanges = () => () => {};

/**
 * Build the services in the browser and provide them below.
 *
 * They are never built while rendering on the server: the static web export
 * renders every route in Node, where there is no `window` for the Auth0 SDK.
 * The server snapshot is "not built", which is also what the browser's first
 * (hydrating) render sees, so consumers show a loading state until then.
 */
export function ServicesProvider({ children }: { children: ReactNode }) {
  const [getBuilt] = useState(() => {
    let built: ServicesState | undefined;
    return () => (built ??= build());
  });
  const state = useSyncExternalStore(neverChanges, getBuilt, () => NOT_BUILT);

  return <ServicesContext.Provider value={state}>{children}</ServicesContext.Provider>;
}

/** The services state provided above, including while it is still building. */
export function useServicesState(): ServicesState {
  return useContext(ServicesContext);
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
