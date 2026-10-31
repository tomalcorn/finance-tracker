# client

The Expo (React Native + react-native-web) TypeScript app that replaces the
Streamlit UI, shipped as an installable web app. See
[ADR 0001](../docs/adr/0001-mobile-via-progressive-web-app.md) for why, and the
[#285 epic](https://github.com/tomalcorn/finance-tracker/issues/285) for what is
being built. It runs against prod Supabase as test users only until the
switch-over.

## Setup

Copy `.env.example` to `.env.local` (gitignored) and fill it in. Every value
is public, because it ends up in the web bundle: the Auth0 domain and SPA
client ID, and prod Supabase's URL and anon key. Log in as a test user from
#283, never your own account, until the switch-over. Run the dev server on
port 8081, the callback URL the Auth0 application allows.

## Commands

Run from `client/`, with Node 22 (`.nvmrc`; Expo SDK 57 needs 22.13+):

| Command                  | What it does                                                                              |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| `npm ci`                 | Install the locked dependencies                                                           |
| `npm run web`            | Start the dev server for the web build (`http://localhost:8081`)                          |
| `npm run lint`           | ESLint (`eslint-config-expo` + Prettier as a rule)                                        |
| `npm run format`         | Format with Prettier (`format:check` to check only)                                       |
| `npm run typecheck`      | `tsc --noEmit`                                                                            |
| `npm test`               | Jest (`test:watch` to watch)                                                              |
| `npm run export:web`     | Build the static web app into `dist/`, with its service worker                            |
| `npm run serve:web`      | Serve `dist/` locally with clean URLs, as a static host would                             |
| `npm run pwa:assets`     | Regenerate the icons, iOS start-up images and manifest from `src/pwa.json`                |
| `npx expo install <pkg>` | Add a dependency at the version matching the Expo SDK; use instead of `npm install <pkg>` |

**Before opening a PR**, run `npm run lint`, `npm run format:check`,
`npm run typecheck` and `npm test`. The `Client Code Quality` workflow runs the
same checks, plus `expo install --check`, on any PR touching `client/`.

## Layout

- `src/app/`: Expo Router routes and layouts only. The root stack holds the
  tab group and Docs. `(tabs)/` holds Quick Expenses (`/`), Personal, Joint and
  Settings, and is only shown when signed in. Signed-out visits are sent to
  `/sign-in`, which remembers where they were going. Docs and sign-in are
  public. The tab layout gates the routes instead of Expo Router's
  `Stack.Protected`, because protected routes get no HTML file in the static
  export, which would break a direct link. It gates each screen through the
  navigator's `screenLayout` rather than rendering something else in place of
  `<Tabs>`: a layout without a navigator loses the URL's tab on the next
  navigation state change, so `usePathname()` reads `/`. Hydrating the static
  export makes such a change before the session loads.
- `src/auth/`: the `AuthClient` port and its implementations:
  `createAuthClient.web.ts` over the Auth0 SPA SDK, and a native stub that is
  always signed out. `AuthProvider` is handed an `AuthClient`, resolves the
  session, and exposes it through `useAuth()`.
- `src/domain/`: zod schemas mirroring the Python `src/domain`. `entities.ts`
  holds the write models (`QuickButtonSchema`, with type `QuickButton`) and
  their rules; `readModels.ts` holds the rows each view returns, computed
  columns included. Field names stay snake_case, as the database has them.
- `src/ports/`: what screens depend on. `Repository<Entity, View>` reads view
  rows and writes whole entities: `build` completes raw rows with the owner and
  validates them (the write gate), then `save` upserts them. An edit is a view
  row with changes merged in, passed back through `build`. `Repositories` gives
  one repository per aggregate and ownership half.
- `src/data/`: the Supabase implementation, the only code that touches
  supabase-js. `TableGateway` pages every select past Supabase's 1,000-row cap.
  `tables.ts` records, for each table, the views and cascades changed by a write
  to it, so that a save marks exactly those cached reads as out of date.
- `src/hooks/`: what screens and components use to reach their dependencies,
  depending only on `src/ports/`. `useRepositories()` gives the signed-in
  user's repositories, and `useRows(repository)` reads one through TanStack
  Query's cache.
- `src/composition/`: the only code that sees every layer. It builds the
  services (`createServices`) in the browser, hands the auth client to
  `AuthProvider`, and `DataProvider` fills in what `src/hooks/` reads. Nothing
  imports it except route files: with Expo Router the routes are the entry
  point, so the layouts act as the composition root. Route tests supply fakes by
  passing `renderRouter` a `wrapper` that sets `ServicesFactoryProvider`, rather
  than mocking modules.
- `src/components/`: shared components, imported as `@/components/...`.
- `__tests__/` directories: tests. Route-level tests sit at the top level,
  and unit tests beside the code they cover. Never put tests inside
  `src/app/`, because every file there becomes a route.

The web build is a static export (`web.output: "static"`), with one HTML file
per route.

## Installing the app (#290)

The web build can be added to a home screen and opens full-screen, with its
shell loaded even with no network.

- `src/pwa.json` holds the installed app's name, colours, icon mark and the
  iPhone screen sizes given a start-up image. `npm run pwa:assets` turns it into
  `public/manifest.json`, `public/icons/`, `public/splash/` and
  `assets/favicon.png`. Commit its output, since the build does not run it. The
  icon is a placeholder `£` until the visual identity (#292); changing it means
  editing `src/pwa.json` and rerunning the script.
- `src/app/+html.tsx` is the HTML around every exported page. It links the
  manifest and adds the iOS home-screen tags and start-up images, plus, in a
  production build only, the service worker registration.
- `npm run export:web` runs Workbox (`workbox-config.cjs`) over `dist/` to write
  `dist/sw.js`. It precaches the shell (HTML, JS, CSS, fonts, icons), ignoring
  query strings, so `/sign-in?returnTo=…` and Auth0's `/?code=…` callback load
  offline too. Nothing else is cached: Supabase and Auth0 are other origins, so
  data always comes from the network. A new deploy takes over the next time the
  app opens.
- Offline, a signed-in user cannot refresh their session, so the app shows
  sign-in rather than their data.

## Deploying (#291)

The `Client Deploy` workflow (`.github/workflows/client-deploy.yml`) builds the
static export against prod Supabase and uploads it to Cloudflare Pages. It runs
on every merge to `main` that touches `client/`, and from **Actions → Client
Deploy → Run workflow**. There are no preview deploys for PRs: login would not
work on them, since Auth0 accepts only the URLs registered with it.

The build stops before deploying if any of the four `EXPO_PUBLIC_` variables
is missing, since the app would otherwise deploy unable to log in.

### One-time setup

1. **Create the Pages project.** Run `npx wrangler login`, then
   `npx wrangler pages project create finance-tracker --production-branch=main`.
   The project's **name** is `finance-tracker`, but its **URL** may carry a
   suffix when the plain name is taken elsewhere: this repo's is
   `https://finance-tracker-drr.pages.dev`. `npx wrangler pages project list`
   shows both.
2. **Create an API token.** In Cloudflare: **My Profile → API Tokens → Create
   Token → Custom token**, with the permission **Account → Cloudflare Pages →
   Edit**, limited to your account. Store it as a repository secret by running
   `gh secret set CLOUDFLARE_API_TOKEN`, which prompts for the value.
3. **Set the repository variables** (Settings → Secrets and variables → Actions
   → Variables, or `gh variable set NAME --body VALUE`):
   - `CLOUDFLARE_ACCOUNT_ID`: shown on the Workers & Pages overview.
   - `CLOUDFLARE_PAGES_PROJECT`: the project's name from step 1
     (`finance-tracker`), not its URL. The deploy stops if it looks like a URL.
   - `EXPO_PUBLIC_AUTH0_DOMAIN`, `EXPO_PUBLIC_AUTH0_CLIENT_ID`,
     `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY`: the same
     values as in `.env.local`. They are public, so they are variables, not
     secrets.
4. **Register the URL in Auth0.** In the "Finance Tracker (web app)"
   application, add the project's URL from step 1 (here
   `https://finance-tracker-drr.pages.dev`, no path and no trailing slash) to
   **Allowed Callback URLs**, **Allowed Logout URLs** and **Allowed Web
   Origins**.
5. **Deploy** with **Run workflow**, or by merging to `main`.

Cloudflare Pages serves `/personal` from `personal.html`, and an unknown path
gets the app's not-found screen: `npm run export:web` copies
`dist/+not-found.html` to `dist/404.html`, the page Pages serves with a 404.

## Decisions (#286)

- **Location:** `client/`, beside the Python code, which is removed at the
  switch-over. Expo Router's routes go in `client/src/app/`.
- **Package manager:** npm, Expo's default; the lockfile is
  `package-lock.json`. Add dependencies with `npx expo install` so they stay
  compatible with the SDK.
- **TypeScript:** `strict`, plus `noUncheckedIndexedAccess` (an indexed read is
  `T | undefined`) and `noImplicitOverride`.
- **Lint and format:** ESLint flat config from `eslint-config-expo`, with
  Prettier run as an ESLint rule and checked on its own in CI. Single quotes,
  100-column lines.
- **Tests:** Jest with the `jest-expo` preset and React Native Testing Library,
  Expo's supported runner for both plain TypeScript and components. Tests live
  in `__tests__/` directories and are named `*-test.ts(x)`.
- **CI:** `.github/workflows/client-code-quality.yml`. Both it and the Python
  `Code Quality` workflow run on every PR. Each skips its jobs when its side of
  the repo is untouched, so a client-only PR does not run the Python suite or
  take the integration-database lock. They skip jobs rather than not running
  at all because the Python jobs are required checks on `main`: a skipped job
  reports and counts as passing, while a workflow that never runs leaves its
  checks pending forever. Client jobs are prefixed `client_`, because required
  checks are matched by job name alone.
- **Versioning:** one version for the whole repo. Commitizen keeps bumping
  `pyproject.toml` and tagging `vX.Y.Z` on merge, and client changes take part
  through ordinary conventional-commit PR titles, scoped `client`
  (`feat(client): …`). `package.json` stays at `0.0.0`, because it is private
  and never published. `app.json`'s `version` only matters for a native build,
  so it is left until one exists.
