-- 0033_user_id_accepts_auth0_sub
--
-- Let `public.user_id()` resolve the caller from an Auth0 ID token as well as
-- from the token Streamlit mints (#284, ADR 0001).
--
-- The Expo app sends Supabase the Auth0 ID token through third-party auth. It
-- carries the user in the standard `sub` claim, whose value is the same Auth0
-- user id Streamlit already stores (Streamlit passes `st.user.sub` as
-- `userId`), so no data changes. Streamlit's minted token has no `sub` and no
-- `iss`, and keeps resolving through `userId` until it is retired, when the
-- fallback is dropped (#308).
--
-- Each claim is trusted only from the issuer that sets it: `sub` when `iss` is
-- the Auth0 tenant, `userId` only when there is no `iss` (Streamlit's minted
-- token). Supabase also accepts tokens from its own Auth service, whose `sub`
-- is a Supabase user uuid; reading `sub` unconditionally would let anyone who
-- signs up there through the anon key act as a user and write rows owned by
-- that uuid. Any other token resolves to no user.
--
-- An unset or empty claims setting also resolves to no user, rather than
-- failing the `::json` cast.
--
-- Every RLS policy calls this function rather than reading claims itself, so
-- this one change covers them all. Prod-only (versions/prod/), like 0005 which
-- defines it: the test database is RLS-free and has no `user_id()`.

CREATE OR REPLACE FUNCTION public.user_id() RETURNS TEXT AS $$
  SELECT NULLIF(
    CASE
      WHEN claims->>'iss' = 'https://st-finance-tracker.eu.auth0.com/'
        THEN claims->>'sub'
      WHEN claims->>'iss' IS NULL
        THEN claims->>'userId'
    END,
    ''
  )::TEXT
  FROM (
    SELECT NULLIF(current_setting('request.jwt.claims', true), '')::json AS claims
  ) AS jwt;
$$ LANGUAGE sql STABLE;
