import { Auth0Client } from '@auth0/auth0-spa-js';

import { type AuthClient, SessionExpiredError } from '@/auth/authClient';
import type { AppConfig } from '@/config';

/** Refresh an ID token this close to expiry rather than send it. */
const ID_TOKEN_MIN_REMAINING_MS = 60_000;

type AppState = { returnTo?: string };

/**
 * Build the browser `AuthClient` over the Auth0 SPA SDK.
 *
 * Tokens are kept in `localStorage` and renewed with rotating refresh tokens,
 * because Safari blocks the third-party cookies silent login otherwise needs.
 */
export function createAuthClient(config: AppConfig): AuthClient {
  const auth0 = new Auth0Client({
    domain: config.auth0Domain,
    clientId: config.auth0ClientId,
    cacheLocation: 'localstorage',
    useRefreshTokens: true,
    authorizationParams: { redirect_uri: window.location.origin },
  });

  async function freshIdToken(): Promise<string> {
    try {
      await auth0.getTokenSilently();
      let claims = await auth0.getIdTokenClaims();
      if (!claims?.exp || claims.exp * 1000 - Date.now() < ID_TOKEN_MIN_REMAINING_MS) {
        await auth0.getTokenSilently({ cacheMode: 'off' });
        claims = await auth0.getIdTokenClaims();
      }
      if (!claims?.__raw) {
        throw new SessionExpiredError();
      }
      return claims.__raw;
    } catch (error) {
      if (error instanceof SessionExpiredError) throw error;
      throw new SessionExpiredError({ cause: error });
    }
  }

  return {
    async handleRedirectCallback() {
      const params = new URLSearchParams(window.location.search);
      if (!params.has('state') || !(params.has('code') || params.has('error'))) {
        return null;
      }
      const { appState } = await auth0.handleRedirectCallback<AppState>();
      window.history.replaceState({}, '', window.location.pathname);
      return appState?.returnTo ?? '/';
    },

    async getUser() {
      try {
        await freshIdToken();
      } catch {
        return null;
      }
      const user = await auth0.getUser();
      return user?.sub ? { sub: user.sub, email: user.email, name: user.name } : null;
    },

    getIdToken: freshIdToken,

    async login(returnTo) {
      await auth0.loginWithRedirect<AppState>({ appState: { returnTo } });
    },

    async logout() {
      await auth0.logout({ logoutParams: { returnTo: window.location.origin } });
    },
  };
}
