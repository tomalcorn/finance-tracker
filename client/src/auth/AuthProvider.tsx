import { type Href, useRouter } from 'expo-router';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react';

import type { AuthUser } from '@/auth/authClient';
import { useServicesState } from '@/composition/ServicesProvider';

/** Where the session stands. `unavailable` means the app cannot authenticate at all. */
export type AuthState =
  | { status: 'loading' }
  | { status: 'signedOut'; error?: string }
  | { status: 'signedIn'; user: AuthUser }
  | { status: 'unavailable'; error: string };

type AuthContextValue = {
  state: AuthState;
  login: (returnTo: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Resolve the session on load, finishing a login redirect if there is one. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const { services, error: servicesError } = useServicesState();
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ status: 'loading' });

  useEffect(() => {
    if (!services) return;
    let cancelled = false;
    (async () => {
      try {
        const returnTo = await services.auth.handleRedirectCallback();
        const user = await services.auth.getUser();
        if (cancelled) return;
        setState(user ? { status: 'signedIn', user } : { status: 'signedOut' });
        if (user && returnTo) router.replace(returnTo as Href);
      } catch (error) {
        if (!cancelled) setState({ status: 'signedOut', error: message(error) });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [services, router]);

  const login = useCallback(
    async (returnTo: string) => {
      try {
        await services?.auth.login(returnTo);
      } catch (error) {
        setState({ status: 'signedOut', error: message(error) });
      }
    },
    [services],
  );

  const logout = useCallback(async () => {
    await services?.auth.logout();
  }, [services]);

  const current: AuthState = servicesError
    ? { status: 'unavailable', error: servicesError.message }
    : state;

  return (
    <AuthContext.Provider value={{ state: current, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** The session and the actions that change it. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside an AuthProvider.');
  }
  return value;
}
