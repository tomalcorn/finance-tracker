import { type Href, useRouter } from 'expo-router';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react';

import type { AuthClient, AuthUser } from '@/auth/authClient';
import { safeReturnTo } from '@/auth/returnTo';
import { MissingProviderError } from '@/hooks/MissingProviderError';

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

/**
 * Resolve the session on load, finishing a login redirect if there is one.
 *
 * `auth` is `null` until it is ready, or for good when it cannot be built,
 * in which case `unavailable` says why.
 */
export function AuthProvider({
  auth,
  unavailable,
  children,
}: {
  auth: AuthClient | null;
  unavailable: Error | null;
  children: ReactNode;
}) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ status: 'loading' });

  useEffect(() => {
    if (!auth) return;
    let cancelled = false;
    (async () => {
      try {
        const returnTo = await auth.handleRedirectCallback();
        const user = await auth.getUser();
        if (cancelled) return;
        setState(user ? { status: 'signedIn', user } : { status: 'signedOut' });
        if (user && returnTo) router.replace(safeReturnTo(returnTo) as Href);
      } catch (error) {
        if (!cancelled) setState({ status: 'signedOut', error: message(error) });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth, router]);

  const login = useCallback(
    async (returnTo: string) => {
      try {
        await auth?.login(safeReturnTo(returnTo));
      } catch (error) {
        setState({ status: 'signedOut', error: message(error) });
      }
    },
    [auth],
  );

  const logout = useCallback(async () => {
    await auth?.logout();
  }, [auth]);

  const current: AuthState = unavailable
    ? { status: 'unavailable', error: unavailable.message }
    : state;

  return (
    <AuthContext.Provider value={{ state: current, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * The session and the actions that change it.
 *
 * @throws {MissingProviderError} when called outside an `AuthProvider`.
 */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new MissingProviderError('useAuth', 'AuthProvider');
  }
  return value;
}
