import type { SupabaseClient } from '@supabase/supabase-js';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import type { AuthClient, AuthUser } from '@/auth/authClient';
import { ConfigError } from '@/config';

const APP_DIR = './src/app';
const USER: AuthUser = { sub: 'auth0|test', email: 'test@example.com' };

let mockAuth: AuthClient;
let mockCreateServicesError: Error | null;

jest.mock('@/composition/createServices', () => ({
  createServices: () => {
    if (mockCreateServicesError) throw mockCreateServicesError;
    return {
      auth: mockAuth,
      supabase: {
        from: () => ({ select: async () => ({ count: 0, error: null }) }),
      } as unknown as SupabaseClient,
    };
  },
}));

function fakeAuth(overrides: Partial<AuthClient> = {}): AuthClient {
  return {
    handleRedirectCallback: async () => null,
    getUser: async () => null,
    getIdToken: async () => 'id-token',
    login: jest.fn(async () => {}),
    logout: jest.fn(async () => {}),
    ...overrides,
  };
}

beforeEach(() => {
  mockAuth = fakeAuth();
  mockCreateServicesError = null;
});

describe('signed out', () => {
  it('sends a tab route to sign-in', async () => {
    const app = renderRouter(APP_DIR, { initialUrl: '/personal' });
    await app;

    await screen.findByText('Log in');
    expect(app.getPathname()).toBe('/sign-in');
  });

  it('logs in returning to the route that was asked for', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/personal' });

    await fireEvent.press(await screen.findByText('Log in'));

    expect(mockAuth.login).toHaveBeenCalledWith('/personal');
  });

  it('leaves docs readable', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/docs' });

    expect(await screen.findByText('Coming in #303.')).toBeOnTheScreen();
  });

  it('shows why the session could not be restored', async () => {
    mockAuth = fakeAuth({
      handleRedirectCallback: async () => {
        throw new Error('access_denied');
      },
    });

    await renderRouter(APP_DIR, { initialUrl: '/' });

    expect(await screen.findByText('access_denied')).toBeOnTheScreen();
  });
});

describe('signed in', () => {
  it('returns to the route a login redirect asked for', async () => {
    mockAuth = fakeAuth({
      handleRedirectCallback: async () => '/joint',
      getUser: async () => USER,
    });

    const app = renderRouter(APP_DIR, { initialUrl: '/' });
    await app;

    await screen.findByText('Coming in #301.');
    expect(app.getPathname()).toBe('/joint');
  });

  it('sends sign-in on to the app', async () => {
    mockAuth = fakeAuth({ getUser: async () => USER });

    const app = renderRouter(APP_DIR, { initialUrl: '/sign-in' });
    await app;

    await screen.findByText('Coming in #295.');
    expect(app.getPathname()).toBe('/');
  });
});

describe('without configuration', () => {
  it('says which variables are missing', async () => {
    mockCreateServicesError = new ConfigError(['EXPO_PUBLIC_AUTH0_CLIENT_ID']);

    await renderRouter(APP_DIR, { initialUrl: '/' });

    expect(await screen.findByText(/EXPO_PUBLIC_AUTH0_CLIENT_ID/)).toBeOnTheScreen();
  });
});
