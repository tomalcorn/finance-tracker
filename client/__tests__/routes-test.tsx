import { QueryClient } from '@tanstack/react-query';
import { renderRouter, screen } from 'expo-router/testing-library';
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
  it.each([
    ['/', 295],
    ['/personal', 293],
    ['/joint', 301],
    ['/settings', 302],
    ['/docs', 303],
  ])('%s renders the screen built in #%i', async (url, issue) => {
    await renderRouter(APP_DIR, { initialUrl: url, wrapper: SignedIn });

    expect(await screen.findByText(`Coming in #${issue}.`)).toBeOnTheScreen();
  });

  it('/design renders the component gallery', async () => {
    await renderRouter(APP_DIR, { initialUrl: '/design', wrapper: SignedIn });

    expect(await screen.findByText('Colours')).toBeOnTheScreen();
  });
});
