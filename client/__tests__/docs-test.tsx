import { QueryClient } from '@tanstack/react-query';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';
import { createRepositories } from '@/data/repositories';
import { GUIDES } from '@/docs/guides';

const APP_DIR = './src/app';

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: 'auth0|test', email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

function emptyRepositories(userId: string) {
  return createRepositories({
    userId,
    gateway: {
      select: async () => [],
      upsert: async () => {},
      delete: async () => {},
      call: async () => {},
    },
    cache: { invalidate: async () => {} },
  });
}

function renderAt(initialUrl: string) {
  const create = (): Services => ({
    auth: SIGNED_IN_AUTH,
    queryClient: new QueryClient({ defaultOptions: { queries: { retry: false } } }),
    repositories: emptyRepositories,
  });
  return renderRouter(APP_DIR, {
    initialUrl,
    wrapper: ({ children }: { children: ReactNode }) => (
      <ServicesFactoryProvider create={create}>{children}</ServicesFactoryProvider>
    ),
  });
}

describe('docs', () => {
  it.each(GUIDES.map((guide) => [guide.title]))('lists %s', async (title) => {
    await renderAt('/docs');

    expect(await screen.findByText(title)).toBeOnTheScreen();
  });

  it('opens a guide from the list', async () => {
    await renderAt('/docs');

    await fireEvent.press(await screen.findByText('Payments'));

    expect(await screen.findByText('Moving money between your own accounts')).toBeOnTheScreen();
  });

  it.each(GUIDES.map((guide) => [guide.slug, guide.title]))(
    'renders /docs/%s',
    async (slug, title) => {
      await renderAt(`/docs/${slug}`);

      expect(await screen.findByRole('heading', { name: title })).toBeOnTheScreen();
    },
  );

  it('follows a link to another guide', async () => {
    await renderAt('/docs/getting_started');

    await fireEvent.press(await screen.findByRole('link', { name: 'subscriptions' }));

    expect(await screen.findByText('How payments get booked')).toBeOnTheScreen();
  });

  it('goes back from a guide opened directly to the list', async () => {
    await renderAt('/docs/payments');

    await fireEvent.press(await screen.findByRole('link', { name: '‹ Back' }));

    expect(await screen.findByText('Getting started')).toBeOnTheScreen();
  });

  it('says when there is no such guide', async () => {
    await renderAt('/docs/nope');

    expect(await screen.findByText(/^There’s no guide here/)).toBeOnTheScreen();
  });
});

describe('links into the guides', () => {
  it.each(['/joint', '/settings'])('%s links to the guide without a joint account', async (url) => {
    await renderAt(url);

    await fireEvent.press(
      await screen.findByRole('button', { name: 'Read the Joint Accounts guide' }),
    );

    expect(await screen.findByText('What is shared and what is not')).toBeOnTheScreen();
  });
});
