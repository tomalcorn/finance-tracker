# 0001. Deliver mobile as an installable web app (PWA) from one TypeScript codebase

- **Status:** Proposed
- **Date:** 2026-09-24
- **Issue:** #279

## Context

The tracker is a Streamlit app. Streamlit runs the page on a Python server and
streams it to the browser over a websocket, so:

- **It cannot run on iOS.** There is no path from Streamlit to a native app. A
  web view wrapping the hosted page is not native, and Apple's App Store
  guideline 4.2 routinely rejects thin wrappers.
- **It is poor on a phone.** The screens are laid out for a wide desktop page
  (`st.set_page_config(layout="wide")`), and the main interaction is editing
  spreadsheet-style grids (`st.data_editor` in `components/dfes/grid.py` and
  `totals.py`). The feature most suited to a phone, one-tap logging from
  Quick Expenses (`pages/quick_expenses.py`), is the one that suffers most.
- **It is clunky on a desktop too.** Almost every screen is a spreadsheet grid,
  so everyday tasks (logging a payment, checking a budget, topping up a goal)
  mean finding the right row and editing cells. Streamlit offers little room to
  build anything friendlier.
- **The hosting sleeps.** Streamlit Community Cloud sleeps after 12 hours with
  no visitors, which is why `ops/keep_awake.py` and the `Keep Awake` workflow
  exist.

The codebase is well placed for a change of front end. Its hexagonal layout
keeps the framework at the edges:

| Layer | Approx. size | Streamlit-coupled? |
| --- | --- | --- |
| `src/domain`, `src/use_cases`, `src/ports` | ~2.9k lines | No: plain Python and pydantic |
| `migrations/` (tables, views, RLS) | 30+ migrations | No: much of the maths already lives in Postgres views, e.g. category accrual and share-of-remaining |
| `src/driven_adapters/supabase` | ~1k lines | Only through `st_supabase_connection` |
| `src/driving_adapters` (pages, blocks, grids, charts) | ~5k lines | Entirely |

One piece of the current design assumes a trusted server.
`SupabaseAuthenticator` signs a short-lived Supabase JWT itself, using the
project's **JWT secret**, with a `userId` claim holding the Auth0 `sub`. RLS
reads that claim through `public.user_id()`
(`migrations/versions/prod/0005_enable_rls.sql`). Code running on a phone or in
a browser can never hold that secret, so any client other than a server needs a
different way to prove who the user is to Supabase.

The constraints for this decision:

1. A good experience on an iPhone, with Quick Expenses as the priority.
2. Ideally **one codebase** serving both phone and desktop.
3. **Free to run.** The Apple Developer Program costs $99/year and is not
   wanted for now.
4. **A friendlier interface.** Move away from grids as the default way of
   working, towards screens built around the tasks people actually do.

## Decision

**Replace the Streamlit UI with an [Expo](https://expo.dev) (React Native +
react-native-web) app written in TypeScript, published only as a static web
app that can be installed from Safari (a Progressive Web App). Supabase stays
as the backend and Auth0 stays as the identity provider.**

In detail:

- **Front end:** Expo with Expo Router, exported as a static web build (`npx
  expo export --platform web`). It includes a web app manifest (name, icons,
  `display: standalone`, theme colour) and a service worker that caches the
  app shell, so it installs to the iOS home screen, opens full-screen, and
  loads instantly.
- **Hosting:** a free static host (Cloudflare Pages, Netlify, Vercel or GitHub
  Pages), deployed from GitHub Actions on merge to `main`.
- **Data:** the app talks to Supabase directly with `@supabase/supabase-js`,
  using only the public anon key. RLS remains the security boundary, exactly as
  it is today.
- **Authentication:** Auth0 login in the browser (Auth0 SPA SDK or
  `expo-auth-session`, using PKCE). Supabase is configured to accept Auth0
  tokens through its **third-party auth** support, so no server has to sign
  tokens. `public.user_id()` is changed to read the Auth0 `sub` claim, falling
  back to `userId` until Streamlit is retired. An Auth0 Action adds the
  `role: authenticated` claim Supabase expects.
- **Business logic:** rules that belong with the data move into Postgres
  (views, and SQL functions called over RPC), continuing the direction the
  migrations already take. Whatever must stay in the client is ported from
  pydantic to TypeScript with [zod](https://zod.dev) schemas, keeping the
  domain / use-case / port split so the architecture carries over as well as
  the code.
- **Interface redesign:** the screens are redesigned, not ported. Grid-heavy
  screens become task-focused views (lists, cards, summaries, forms and
  progress visuals), with a refreshed visual identity shared across the app.
  Tables stay only where working with many rows at once genuinely needs them.
  The detailed design is left to the work itself, starting with Quick
  Expenses.
- **One switch-over, not a gradual migration.** The Expo app is built up
  alongside Streamlit until it covers everything Streamlit does, but it is
  only used for testing in the meantime. Streamlit stays the only app in real
  use until the new one is ready, then it is replaced in a single cut-over and
  retired.
- **No App Store and no Apple Developer Program.** Because the app is built on
  React Native rather than as a plain website, the same codebase can later
  produce a native iOS build through EAS if that becomes worth $99/year. That
  would be an addition, not a rewrite.

## Options considered

| Option | One codebase | Native on iOS | Cost | Verdict |
| --- | --- | --- | --- | --- |
| **Expo, shipped as a PWA** (chosen) | Yes | No for now; possible later from the same code | Free | Best fit: free, one codebase, keeps the native option open |
| Plain web SPA as a PWA (React/Vite, SvelteKit) | Yes | No, and never without a rewrite | Free | Slightly simpler web stack, but closes off going native |
| Expo, shipped to the App Store | Yes | Yes | $99/year | Deferred rather than rejected: same code, paid later if wanted |
| Flutter | Yes | Yes | $99/year to ship natively | Viable, but Flutter web draws its UI on a canvas, which is weaker for a web-first PWA (text selection, accessibility, bundle size) |
| Flet (Python on Flutter) | Yes, and stays in Python | Mostly | $99/year to ship natively | Only option that keeps the Python domain code as is, but its iOS support is young, and it inherits Flutter's web weaknesses |
| Capacitor wrapping a web app | Yes | No (web view) | $99/year | Pays for the App Store without getting a native app |
| SwiftUI app + keep Streamlit (FastAPI in front of the existing use cases) | No, two UIs | Yes, best possible | $99/year plus a server | Most native, but two front ends and a server to run and pay for |
| Keep Streamlit, tune it for mobile | Yes | No | Free | Cannot fix the grid-heavy interaction model, sleeping hosting or offline start-up, and leaves little room for a redesign |

## Consequences

### Positive

- **Free to run.** The costs are all free tiers: Supabase, Auth0 (its free
  plan covers far more users than this app needs), a static host and GitHub
  Actions. There is no Apple fee and no server to host.
- **No more sleeping.** A static site is always available, so
  `ops/keep_awake.py` and the `Keep Awake` workflow can be deleted once
  Streamlit is retired.
- **A friendlier app.** Rebuilding the UI is the chance to redesign it, so the
  migration and the move away from spreadsheet-style editing are one piece of
  work rather than two.
- **Faster and phone-friendly.** Screens are built for touch and small widths.
  The installed app opens full-screen from the home screen, the app shell loads
  from cache, and data comes straight from Supabase instead of through a
  Streamlit server.
- **Safer authentication.** The Supabase JWT secret leaves the app entirely.
  Nothing outside Supabase can mint a valid token.
- **The native option stays open.** Widgets, Siri Shortcuts and the App Store
  become a later build target, not a rewrite.

### Negative / trade-offs

- **It is a rewrite of the UI** (~5k lines) and a port of the domain and
  use-case layers (~3k lines) from Python to TypeScript. The existing pytest
  suite does not carry over; tests are rewritten, e.g. with Vitest, alongside
  the code they cover.
- **Redesign adds design work to every screen.** Nothing can be carried over
  as it looks today, and each screen needs its interactions worked out (and
  checked on both phone and desktop widths) before it is built. Bulk edits that
  a grid makes trivial need a deliberate replacement where they are still
  wanted.
- **Nothing pays off until the switch-over.** The phone gets no benefit from
  the new app, Quick Expenses included, until it has caught up with
  Streamlit completely.
- **Two codebases share one schema** while the new app is built. Streamlit
  stays the live app, so any schema change made for the Expo app must keep
  Streamlit working, and anything added to Streamlit in the meantime widens
  the gap the new app has to close. Keeping new Streamlit features to a
  minimum during the build keeps that gap from moving.
- **iOS limits on installed web apps:**
  - no home-screen widgets, Siri Shortcuts or App Store listing
  - push notifications work only after the app is installed to the home
    screen (iOS 16.4+) and the user grants permission
  - Safari may clear an installed app's storage if it goes unused for weeks,
    so nothing important may be stored only on the device; Supabase stays the
    source of truth
- **The Supabase free tier still pauses** a project after about a week with no
  activity. This is unchanged from today.

### Risks and checks before building

These depend on third-party products and must be confirmed against current
documentation when work starts:

- Supabase third-party auth supports Auth0 on the free plan, and how it
  expects the `role` claim to be set.
- The exact claim `public.user_id()` should read from an Auth0 token (`sub` is
  expected to match today's `userId` values, since both come from the Auth0
  `sub`).
- Current free-tier limits of the chosen static host and of Supabase.
- Expo's current guidance on web manifests and service workers for static web
  exports.

## Plan

Streamlit stays the live app throughout steps 1 to 3. Only step 4 changes what
is used day to day.

1. **Authentication without the JWT secret.**
   - Enable Supabase third-party auth for Auth0, and add an Auth0 Action that
     sets `role: authenticated`.
   - Add a migration so `public.user_id()` accepts `sub` as well as `userId`,
     so Streamlit's minted tokens keep working alongside Auth0's.
2. **Scaffold the Expo app.**
   - Expo + Expo Router + TypeScript, supabase-js, Auth0 login, the manifest,
     the service worker, and a CI deployment to the static host, pointed at
     the Supabase project.
   - Set up the new visual identity (theme, typography, icons) and the shared
     components the screens will reuse.
3. **Build the screens until the app covers everything Streamlit does:**
   Quick Expenses first, then Personal (budget, payments, subscriptions, bank
   accounts, one-offs, summary), Joint, Settings and the in-app docs
   (`src/docs/*.md`). Each is redesigned rather than a reproduction of its
   grids. Logic that belongs with the data moves into Postgres views or SQL
   functions as each screen needs it, which shrinks what has to be written in
   TypeScript. The app is used only for testing during this step.
4. **Switch over and retire Streamlit.**
   - Remove `src/driving_adapters`, `streamlit_app.py`, the Streamlit
     dependencies, `SupabaseAuthenticator` and the JWT secret,
     `ops/keep_awake.py` and the `Keep Awake` workflow.
   - Drop the `userId` fallback from `public.user_id()`.
   - The Python `migrations/` tooling stays for schema changes.

### Revisit this decision if

- widgets, Siri Shortcuts, or reliable notifications become important enough
  to justify $99/year: add an EAS iOS build from the same codebase
- Apple materially restricts installed web apps on iOS
- the Supabase free tier stops covering the app's needs
