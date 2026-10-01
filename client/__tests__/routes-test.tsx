import type { SupabaseClient } from '@supabase/supabase-js';
import { renderRouter, screen } from 'expo-router/testing-library';

import type { AuthClient } from '@/auth/authClient';
import type { Services } from '@/composition/createServices';

const APP_DIR = './src/app';

const mockSignedInAuth: AuthClient = {
  handleRedirectCallback: async () => null,
  getUser: async () => ({ sub: 'auth0|test', email: 'test@example.com' }),
  getIdToken: async () => 'id-token',
  login: async () => {},
  logout: async () => {},
};

const mockSupabase = {
  from: () => ({ select: async () => ({ count: 0, error: null }) }),
} as unknown as SupabaseClient;

jest.mock('@/composition/createServices', () => ({
  createServices: (): Services => ({ auth: mockSignedInAuth, supabase: mockSupabase }),
}));

describe('routes when signed in', () => {
  it.each([
    ['/', 295],
    ['/personal', 293],
    ['/joint', 301],
    ['/settings', 302],
    ['/docs', 303],
  ])('%s renders the screen built in #%i', async (url, issue) => {
    await renderRouter(APP_DIR, { initialUrl: url });

    expect(await screen.findByText(`Coming in #${issue}.`)).toBeOnTheScreen();
  });
});
