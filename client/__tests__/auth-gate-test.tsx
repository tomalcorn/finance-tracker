import { QueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { act, fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient, AuthUser } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { createRepositories } from '@/data/repositories';
import { ConfigError } from '@/config';

const APP_DIR = './src/app';
const USER: AuthUser = { sub: 'auth0|test', email: 'test@example.com' };

/** Repositories over an empty in-memory gateway. */
function emptyRepositories(userId: string) {
  return createRepositories({
    userId,
    gateway: { select: async () => [], upsert: async () => {}, delete: async () => {} },
    cache: { invalidate: async () => {} },
  });
}

function fakeServices(auth: AuthClient): Services {
  return {
    auth,
    queryClient: new QueryClient({ defaultOptions: { queries: { retry: false } } }),
    repositories: emptyRepositories,
  };
}

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
  return renderApp(initialUrl, () => fakeServices(auth));
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
    await screen.findByRole('heading', { name: 'Quick Expenses' });

    expect(replace).toHaveBeenLastCalledWith('/');
  });

  it('sends sign-in on to the app', async () => {
    const app = renderWithAuth('/sign-in', fakeAuth({ getUser: async () => USER }));
    await app;

    await screen.findByRole('heading', { name: 'Quick Expenses' });
    expect(app.getPathname()).toBe('/');
  });
});

/**
 * Render `initialUrl` and change the navigation state while the session is still loading.
 *
 * Hydrating the static web export makes that change on its own; `renderRouter`
 * does not hydrate, so this makes it with `setParams` instead.
 */
async function renderWithStateChangeWhileLoading(initialUrl: string, user: AuthUser | null) {
  let finishLoading = () => {};
  const loaded = new Promise<null>((resolve) => {
    finishLoading = () => resolve(null);
  });
  const auth = fakeAuth({ handleRedirectCallback: () => loaded, getUser: async () => user });
  const app = renderWithAuth(initialUrl, auth);
  await app;

  await act(() => router.setParams({}));
  await act(async () => finishLoading());

  return { app, auth };
}

describe('a navigation state change while the session loads', () => {
  it('logs in returning to the route that was asked for', async () => {
    const { auth } = await renderWithStateChangeWhileLoading('/personal', null);

    await fireEvent.press(await screen.findByText('Log in'));

    expect(auth.login).toHaveBeenCalledWith('/personal');
  });

  it('opens the route that was asked for once signed in', async () => {
    const { app } = await renderWithStateChangeWhileLoading('/joint', USER);

    await screen.findByText('Coming in #301.');
    expect(app.getPathname()).toBe('/joint');
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
