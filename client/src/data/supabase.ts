import { createClient, type SupabaseClient } from '@supabase/supabase-js';

import type { AppConfig } from '@/config';

/**
 * Build the Supabase client, authenticated with the user's Auth0 ID token.
 *
 * Supabase accepts Auth0 tokens through third-party auth, and RLS reads the
 * user from their `sub` claim, so only the public anon key is needed.
 * `getIdToken` runs before every request, so a token is never sent stale.
 */
export function createSupabase(
  config: AppConfig,
  getIdToken: () => Promise<string>,
): SupabaseClient {
  return createClient(config.supabaseUrl, config.supabaseAnonKey, {
    accessToken: getIdToken,
  });
}
