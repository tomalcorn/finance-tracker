/** The signed-in user, from the Auth0 ID token. */
export type AuthUser = {
  sub: string;
  email?: string;
  name?: string;
};

/** What the app needs from an identity provider. */
export interface AuthClient {
  /**
   * Finish a login redirect if the current URL is one.
   *
   * @returns the path to return to after a completed login, or `null` when the
   *   URL was not a login redirect.
   */
  handleRedirectCallback(): Promise<string | null>;

  /** The signed-in user, refreshing the session if needed; `null` when signed out. */
  getUser(): Promise<AuthUser | null>;

  /**
   * A current, unexpired ID token: what Supabase is sent.
   *
   * @throws {SessionExpiredError} when the session can no longer be refreshed.
   */
  getIdToken(): Promise<string>;

  /** Start a login, returning to `returnTo` afterwards. */
  login(returnTo: string): Promise<void>;

  /** End the session at the identity provider and locally. */
  logout(): Promise<void>;
}

/** The session ended and could not be refreshed; the user must log in again. */
export class SessionExpiredError extends Error {
  constructor(options?: { cause?: unknown }) {
    super('Your session has expired. Log in again.', options);
    this.name = 'SessionExpiredError';
  }
}
