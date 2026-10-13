import { type AuthClient, SessionExpiredError } from '@/auth/authClient';
import type { AppConfig } from '@/config';

/**
 * Build the native `AuthClient`: not implemented yet, so the app is always
 * signed out off the web. The web build uses `createAuthClient.web.ts`.
 */
export function createAuthClient(_config: AppConfig): AuthClient {
  return {
    handleRedirectCallback: async () => null,
    getUser: async () => null,
    getIdToken: async () => {
      throw new SessionExpiredError();
    },
    login: async () => {
      throw new Error('Login is only implemented for the web build so far.');
    },
    logout: async () => {},
  };
}
