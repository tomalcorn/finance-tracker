# client

The Expo (React Native + react-native-web) TypeScript app that replaces the
Streamlit UI, shipped as an installable web app. See
[ADR 0001](../docs/adr/0001-mobile-via-progressive-web-app.md) for why, and the
[#285 epic](https://github.com/tomalcorn/finance-tracker/issues/285) for what is
being built. It runs against prod Supabase as test users only until the
switch-over.

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
| `npx expo install <pkg>` | Add a dependency at the version matching the Expo SDK; use instead of `npm install <pkg>` |

**Before opening a PR**, run `npm run lint`, `npm run format:check`,
`npm run typecheck` and `npm test`. The `Client Code Quality` workflow runs the
same checks, plus `expo install --check`, on any PR touching `client/`.

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
