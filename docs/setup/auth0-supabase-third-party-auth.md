# Auth0 → Supabase third-party auth

How prod Supabase is set up to accept Auth0 ID tokens, so the Expo app can talk
to it directly with only the anon key. Background: [ADR 0001](../adr/0001-mobile-via-progressive-web-app.md)
and the findings on #282.

Nothing here changes how Streamlit authenticates. It keeps minting its own
tokens with the JWT secret until the switch-over.

- **Auth0 tenant:** `st-finance-tracker`, region `eu`
  (`https://st-finance-tracker.eu.auth0.com/`)
- **Supabase project:** prod only. The testing database has no RLS and is not
  used by the Expo app.

## 1. Auth0: add the `role` claim to ID tokens

Supabase needs a literal `role: authenticated` claim. Auth0 strips
un-namespaced custom claims from access tokens, so the claim goes on the ID
token, which is what the app sends Supabase.

1. Auth0 Dashboard → **Actions → Library → Create Action → Build from scratch**.
   - Name: `Supabase role claim`
   - Trigger: **Login / Post Login**
   - Runtime: the default (latest Node)
2. Replace the code with:

   ```js
   exports.onExecutePostLogin = async (event, api) => {
     api.idToken.setCustomClaim('role', 'authenticated');
   };
   ```

3. **Deploy**.
4. **Actions → Triggers → post-login**: drag `Supabase role claim` into the
   flow, then **Apply**.

The Action runs for every application in the tenant, Streamlit's included.
That is harmless: Streamlit reads only `sub` from its ID token.

## 2. Auth0: create the SPA application

The existing application is a Regular Web App with a client secret, used by
`st.login("auth0")`. The browser app needs its own.

1. **Applications → Applications → Create Application**.
   - Name: `Finance Tracker (web app)`
   - Type: **Single Page Web Applications**
2. **Settings** tab:
   - **Allowed Callback URLs**, **Allowed Logout URLs** and **Allowed Web
     Origins**: `http://localhost:8081` for now (Expo's web dev server, and the
     verification page below). The deployed URL is added in #291.
   - **Refresh Token Rotation**: on. Safari blocks the third-party cookies
     silent login relies on, so the app stays logged in with rotating refresh
     tokens instead.
   - **Refresh Token Expiration**: keep **Absolute Expiration** on, with an
     **Inactivity Expiration** of your choosing (e.g. 30 days).
   - **Advanced Settings → OAuth → JSON Web Token (JWT) Signature Algorithm**:
     **RS256** (the default). Supabase rejects HS256 and PS256.
3. **Connections** tab: enable the same connections you log in to Streamlit
   with, plus **Username-Password-Authentication** for the test users.
4. Note the **Client ID** (it is public, not a secret).

## 3. Auth0: create the test users

All Expo testing happens as these users, so RLS keeps it away from real data.

1. **User Management → Users → Create User**, connection
   **Username-Password-Authentication**:
   - `test-user-1` (e.g. an address you control with a `+test1` suffix)
   - `test-user-2`, for joint-account testing later
2. Keep the passwords in your password manager, not in the repo.

## 4. Supabase: enable Auth0 as a third-party provider

1. Supabase Dashboard → the **prod** project → **Authentication → Sign In /
   Providers → Third-Party Auth** → **Add provider → Auth0**.
2. Tenant ID: `st-finance-tracker`, region: `eu`.
3. Save. Supabase fetches the tenant's signing keys from its JWKS; key changes
   can take up to 30 minutes to be picked up.

## 5. Verify

[`verify-third-party-auth.html`](./verify-third-party-auth.html) logs in with
the SPA application and calls prod's REST API with the ID token.

```bash
python3 -m http.server 8081 --directory docs/setup
```

Open <http://localhost:8081/verify-third-party-auth.html>. Enter the Auth0 SPA
client ID and the prod project URL and anon key (from `.streamlit/secrets.toml`),
then log in as `test-user-1`. The fields are kept only in the browser's
`localStorage`.

Expected results:

| Check | Expected |
| --- | --- |
| ID token claims | `role: "authenticated"`, `sub` like `auth0|…`, `iss` the tenant URL |
| Request with the ID token | **200**, `[]`: accepted, no rows yet |
| Request with a corrupted token | **401**: tokens really are being checked |

Until #284 lands, `public.user_id()` reads only `userId`, so an Auth0 token
resolves to no user and every table reads empty. **200 rather than 401 is the
pass condition for this step.** Also check Streamlit still logs in and shows
your data.
