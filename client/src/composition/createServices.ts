import type { SupabaseClient } from '@supabase/supabase-js';

import type { AuthClient } from '@/auth/authClient';
import { createAuthClient } from '@/auth/createAuthClient';
import { loadConfig } from '@/config';
import { createSupabase } from '@/data/supabase';

/** The app's outbound dependencies, built once per page load. */
export type Services = {
  auth: AuthClient;
  supabase: SupabaseClient;
};

/**
 * Build the real services from the bundled configuration.
 *
 * @throws {ConfigError} when the configuration is incomplete.
 */
export function createServices(): Services {
  const config = loadConfig();
  const auth = createAuthClient(config);
  return { auth, supabase: createSupabase(config, () => auth.getIdToken()) };
}
