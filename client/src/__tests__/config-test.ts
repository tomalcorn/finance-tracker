import { ConfigError, type ConfigValues, parseConfig } from '@/config';

const FULL: ConfigValues = {
  EXPO_PUBLIC_AUTH0_DOMAIN: 'tenant.eu.auth0.com',
  EXPO_PUBLIC_AUTH0_CLIENT_ID: 'client-id',
  EXPO_PUBLIC_SUPABASE_URL: 'https://project.supabase.co',
  EXPO_PUBLIC_SUPABASE_ANON_KEY: 'anon-key',
};

describe('parseConfig', () => {
  it('maps every variable', () => {
    expect(parseConfig(FULL)).toEqual({
      auth0Domain: 'tenant.eu.auth0.com',
      auth0ClientId: 'client-id',
      supabaseUrl: 'https://project.supabase.co',
      supabaseAnonKey: 'anon-key',
    });
  });

  it('names every missing or empty variable', () => {
    const values = {
      ...FULL,
      EXPO_PUBLIC_AUTH0_CLIENT_ID: '',
      EXPO_PUBLIC_SUPABASE_URL: undefined,
    };

    expect(() => parseConfig(values)).toThrow(
      expect.objectContaining({
        constructor: ConfigError,
        missing: ['EXPO_PUBLIC_AUTH0_CLIENT_ID', 'EXPO_PUBLIC_SUPABASE_URL'],
      }),
    );
  });
});
