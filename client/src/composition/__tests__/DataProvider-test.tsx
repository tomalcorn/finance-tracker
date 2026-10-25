import { render } from '@testing-library/react-native';

import { createServices } from '@/composition/createServices';
import { DataProvider } from '@/composition/DataProvider';
import { ServicesFactoryProvider, ServicesProvider } from '@/composition/ServicesProvider';
import { useRepositories } from '@/hooks/repositories';
import type { Repositories } from '@/ports/repositories';

const CONFIG = {
  EXPO_PUBLIC_AUTH0_DOMAIN: 'tenant.eu.auth0.com',
  EXPO_PUBLIC_AUTH0_CLIENT_ID: 'client-id',
  EXPO_PUBLIC_SUPABASE_URL: 'https://project.supabase.co',
  EXPO_PUBLIC_SUPABASE_ANON_KEY: 'anon-key',
};

const ORIGINAL_ENV = { ...process.env };

beforeEach(() => {
  Object.assign(process.env, CONFIG);
  // Supabase's realtime client warns about the native auth stub's missing token.
  jest.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  for (const name of Object.keys(CONFIG)) {
    delete process.env[name];
  }
  Object.assign(process.env, ORIGINAL_ENV);
  jest.restoreAllMocks();
});

/** Render one `DataProvider` per user id, all over one set of real services. */
async function repositoriesSeenBy(userIds: readonly string[]): Promise<Repositories[]> {
  const seen: Repositories[] = [];
  function Probe() {
    seen.push(useRepositories());
    return null;
  }

  await render(
    <ServicesFactoryProvider create={createServices}>
      <ServicesProvider>
        {userIds.map((userId, index) => (
          <DataProvider key={index} userId={userId}>
            <Probe />
          </DataProvider>
        ))}
      </ServicesProvider>
    </ServicesFactoryProvider>,
  );

  return seen;
}

describe('DataProvider', () => {
  it('shares one set of repositories between providers for the same user', async () => {
    const [first, second] = await repositoriesSeenBy(['auth0|a', 'auth0|a']);

    expect(second).toBe(first);
  });

  it('gives a different user their own repositories', async () => {
    const [first, second] = await repositoriesSeenBy(['auth0|a', 'auth0|b']);

    expect(second).not.toBe(first);
  });
});
