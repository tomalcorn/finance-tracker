import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { createRepositories } from '@/data/repositories';

const APP_DIR = './src/app';

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: 'auth0|test', email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

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

const createSignedIn = (): Services => fakeServices(SIGNED_IN_AUTH);

function SignedIn({ children }: { children: ReactNode }) {
  return <ServicesFactoryProvider create={createSignedIn}>{children}</ServicesFactoryProvider>;
}

describe('routes when signed in', () => {
  it('/ renders Quick Expenses', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/', wrapper: SignedIn });

    expect(await screen.findByText('No quick buttons yet')).toBeOnTheScreen();
  });

  it('/personal renders the budget overview', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/personal', wrapper: SignedIn });

    expect(await screen.findByText('Budget trackers')).toBeOnTheScreen();
  });

  it('/joint explains there is no joint account yet', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/joint', wrapper: SignedIn });

    expect(await screen.findByText('You don’t have a joint account yet.')).toBeOnTheScreen();
  });

  it.each([
    ['/settings', 302],
    ['/docs', 303],
  ])('%s renders the screen built in #%i', async (url, issue) => {
    await renderRouter(APP_DIR, { initialUrl: url, wrapper: SignedIn });

    expect(await screen.findByText(`Coming in #${issue}.`)).toBeOnTheScreen();
  });

  it('switches screen when a tab is pressed', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/', wrapper: SignedIn });

    await fireEvent.press(await screen.findByRole('tab', { name: 'Settings' }));

    expect(await screen.findByText('Coming in #302.')).toBeOnTheScreen();
  });

  it('/design renders the component gallery', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/design', wrapper: SignedIn });

    expect(await screen.findByText('Colours')).toBeOnTheScreen();
  });
});
