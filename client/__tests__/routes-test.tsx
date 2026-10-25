import type { SupabaseClient } from '@supabase/supabase-js';
import { renderRouter, screen } from 'expo-router/testing-library';
import type { ReactNode } from 'react';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';
import { ServicesFactoryProvider } from '@/composition/ServicesProvider';

const APP_DIR = './src/app';

const SIGNED_IN_AUTH: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: 'auth0|test', email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

const FAKE_SUPABASE = {
  from: () => ({ select: async () => ({ count: 0, error: null }) }),
} as unknown as SupabaseClient;

const createSignedIn = (): Services => ({ auth: SIGNED_IN_AUTH, supabase: FAKE_SUPABASE });

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
});
