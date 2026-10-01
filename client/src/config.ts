/** Public configuration baked into the bundle from `EXPO_PUBLIC_` variables. */
export type AppConfig = {
  auth0Domain: string;
  auth0ClientId: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
};

/** A required `EXPO_PUBLIC_` variable is missing or empty. */
export class ConfigError extends Error {
  readonly missing: readonly string[];

  constructor(missing: readonly string[]) {
    super(`Missing configuration: ${missing.join(', ')}. See client/.env.example.`);
    this.name = 'ConfigError';
    this.missing = missing;
  }
}

/** The raw `EXPO_PUBLIC_` variables `loadConfig` reads. */
export type ConfigValues = {
  EXPO_PUBLIC_AUTH0_DOMAIN?: string;
  EXPO_PUBLIC_AUTH0_CLIENT_ID?: string;
  EXPO_PUBLIC_SUPABASE_URL?: string;
  EXPO_PUBLIC_SUPABASE_ANON_KEY?: string;
};

/**
 * Validate raw configuration values.
 *
 * @throws {ConfigError} when any value is missing or empty.
 */
export function parseConfig(values: ConfigValues): AppConfig {
  const required = {
    EXPO_PUBLIC_AUTH0_DOMAIN: values.EXPO_PUBLIC_AUTH0_DOMAIN,
    EXPO_PUBLIC_AUTH0_CLIENT_ID: values.EXPO_PUBLIC_AUTH0_CLIENT_ID,
    EXPO_PUBLIC_SUPABASE_URL: values.EXPO_PUBLIC_SUPABASE_URL,
    EXPO_PUBLIC_SUPABASE_ANON_KEY: values.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  };
  const missing = Object.entries(required)
    .filter(([, value]) => !value)
    .map(([name]) => name);
  if (missing.length > 0) {
    throw new ConfigError(missing);
  }
  return {
    auth0Domain: required.EXPO_PUBLIC_AUTH0_DOMAIN!,
    auth0ClientId: required.EXPO_PUBLIC_AUTH0_CLIENT_ID!,
    supabaseUrl: required.EXPO_PUBLIC_SUPABASE_URL!,
    supabaseAnonKey: required.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  };
}

/**
 * Read the app's configuration from the bundle.
 *
 * Each variable is read as a literal `process.env.EXPO_PUBLIC_…` expression
 * because Expo inlines them at build time only in that form.
 *
 * @throws {ConfigError} when any variable is missing or empty.
 */
export function loadConfig(): AppConfig {
  return parseConfig({
    EXPO_PUBLIC_AUTH0_DOMAIN: process.env.EXPO_PUBLIC_AUTH0_DOMAIN,
    EXPO_PUBLIC_AUTH0_CLIENT_ID: process.env.EXPO_PUBLIC_AUTH0_CLIENT_ID,
    EXPO_PUBLIC_SUPABASE_URL: process.env.EXPO_PUBLIC_SUPABASE_URL,
    EXPO_PUBLIC_SUPABASE_ANON_KEY: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  });
}
