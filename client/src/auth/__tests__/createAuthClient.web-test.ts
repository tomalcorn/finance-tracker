import { SessionExpiredError } from '@/auth/authClient';
import { createAuthClient } from '@/auth/createAuthClient.web';
import type { AppConfig } from '@/config';

const CONFIG: AppConfig = {
  auth0Domain: 'tenant.eu.auth0.com',
  auth0ClientId: 'client-id',
  supabaseUrl: 'https://project.supabase.co',
  supabaseAnonKey: 'anon-key',
};

type Claims = { __raw: string; exp: number };

const mockAuth0 = {
  getTokenSilently: jest.fn(),
  getIdTokenClaims: jest.fn(),
};

jest.mock('@auth0/auth0-spa-js', () => ({
  Auth0Client: jest.fn(() => mockAuth0),
}));

function claimsExpiringIn(ms: number, raw: string): Claims {
  return { __raw: raw, exp: (Date.now() + ms) / 1000 };
}

beforeAll(() => {
  Object.defineProperty(globalThis, 'window', {
    value: { location: { origin: 'http://localhost:8081', search: '', pathname: '/' } },
    configurable: true,
  });
});

beforeEach(() => {
  mockAuth0.getTokenSilently.mockReset().mockResolvedValue('access-token');
  mockAuth0.getIdTokenClaims.mockReset();
});

describe('getIdToken', () => {
  it('returns the cached ID token while it has time left', async () => {
    mockAuth0.getIdTokenClaims.mockResolvedValue(claimsExpiringIn(3_600_000, 'cached'));

    await expect(createAuthClient(CONFIG).getIdToken()).resolves.toBe('cached');
  });

  it('refreshes an ID token about to expire', async () => {
    mockAuth0.getIdTokenClaims
      .mockResolvedValueOnce(claimsExpiringIn(30_000, 'stale'))
      .mockResolvedValueOnce(claimsExpiringIn(3_600_000, 'fresh'));

    await expect(createAuthClient(CONFIG).getIdToken()).resolves.toBe('fresh');
  });

  it('bypasses the cache when refreshing', async () => {
    mockAuth0.getIdTokenClaims
      .mockResolvedValueOnce(claimsExpiringIn(30_000, 'stale'))
      .mockResolvedValueOnce(claimsExpiringIn(3_600_000, 'fresh'));

    await createAuthClient(CONFIG).getIdToken();

    expect(mockAuth0.getTokenSilently).toHaveBeenLastCalledWith({ cacheMode: 'off' });
  });

  it('reports a session that cannot be refreshed as expired', async () => {
    mockAuth0.getTokenSilently.mockRejectedValue(new Error('missing_refresh_token'));

    await expect(createAuthClient(CONFIG).getIdToken()).rejects.toBeInstanceOf(SessionExpiredError);
  });
});
