import type { SupabaseClient } from '@supabase/supabase-js';
import { router } from 'expo-router';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient, AuthUser } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { ConfigError } from '@/config';

const APP_DIR = './src/app';
const USER: AuthUser = { sub: 'auth0|test', email: 'test@example.com' };

const FAKE_SUPABASE = {
  from: () => ({ select: async () => ({ count: 0, error: null }) }),
} as unknown as SupabaseClient;

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

function renderApp(initialUrl: string, create: () => Services) {
  return renderRouter(APP_DIR, {
    initialUrl,
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

function renderWithAuth(initialUrl: string, auth: AuthClient) {
  return renderApp(initialUrl, () => ({ auth, supabase: FAKE_SUPABASE }));
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe('signed out', () => {
  it('sends a tab route to sign-in', async () => {
    const app = renderWithAuth('/personal', fakeAuth());
    await app;

    await screen.findByText('Log in');
    expect(app.getPathname()).toBe('/sign-in');
  });

  it('logs in returning to the route that was asked for', async () => {
    const auth = fakeAuth();
    await renderWithAuth('/personal', auth);

    await fireEvent.press(await screen.findByText('Log in'));

    expect(auth.login).toHaveBeenCalledWith('/personal');
  });

  it('logs in returning home when asked to return off the app', async () => {
    const auth = fakeAuth();
    await renderWithAuth('/sign-in?returnTo=https%3A%2F%2Fevil.example', auth);

    await fireEvent.press(await screen.findByText('Log in'));

    expect(auth.login).toHaveBeenCalledWith('/');
  });

  it('leaves docs readable', async () => {
    await renderWithAuth('/docs', fakeAuth());

    expect(await screen.findByText('Coming in #303.')).toBeOnTheScreen();
  });

  it('shows why the session could not be restored', async () => {
    const auth = fakeAuth({
      handleRedirectCallback: async () => {
        throw new Error('access_denied');
      },
    });

    await renderWithAuth('/', auth);

    expect(await screen.findByText('access_denied')).toBeOnTheScreen();
  });
});

describe('signed in', () => {
  it('returns to the route a login redirect asked for', async () => {
    const auth = fakeAuth({
      handleRedirectCallback: async () => '/joint',
      getUser: async () => USER,
    });

    const app = renderWithAuth('/', auth);
    await app;

    await screen.findByText('Coming in #301.');
    expect(app.getPathname()).toBe('/joint');
  });

  it('returns home when a login redirect asks to leave the app', async () => {
    const replace = jest.spyOn(router, 'replace');
    const auth = fakeAuth({
      handleRedirectCallback: async () => 'https://evil.example',
      getUser: async () => USER,
    });

    await renderWithAuth('/', auth);
    await screen.findByText('Coming in #295.');

    expect(replace).toHaveBeenLastCalledWith('/');
  });

  it('sends sign-in on to the app', async () => {
    const app = renderWithAuth('/sign-in', fakeAuth({ getUser: async () => USER }));
    await app;

    await screen.findByText('Coming in #295.');
    expect(app.getPathname()).toBe('/');
  });
});

describe('without configuration', () => {
  it('says which variables are missing', async () => {
    await renderApp('/', () => {
      throw new ConfigError(['EXPO_PUBLIC_AUTH0_CLIENT_ID']);
    });

    expect(await screen.findByText(/EXPO_PUBLIC_AUTH0_CLIENT_ID/)).toBeOnTheScreen();
  });
});
