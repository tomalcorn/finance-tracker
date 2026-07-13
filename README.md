# finance-tracker

A Streamlit app for tracking personal finances across bank accounts, budget
categories, recurring subscriptions, payments, and one-off savings goals.

The app code lives under `src/`. For a guided walkthrough of each block and
how to use the tracker effectively, see the [markdown docs](./src/docs/01_getting_started.md).

## Data Flow At A Glance

```text
Auth0 login
   |
   v
Streamlit session
   |
   v
Supabase tables and views
   |
   +--> dashboard blocks
   +--> computed metrics
   +--> add/filter dialogs
```

## Database migrations

SQL schema and view changes are versioned as ordered `NNNN_description.sql`
files under [`sql_stuff/migrations/`](./sql_stuff/migrations/README.md) and
applied by a small runner (`src/driven_adapters/migrations/`) that records what
it has applied in a `schema_migrations` table, so re-runs only apply pending
files.

```bash
uv run poe migrate            # apply pending migrations to the testing DB
uv run poe migrate --env prod # apply pending migrations to prod
uv run poe migrate --status   # list applied / pending, change nothing
uv run poe migrate --baseline # record present migrations as applied, run none
```

The app talks to Supabase over PostgREST (which can't run DDL), so the runner
needs a **direct Postgres connection string**, resolved from `DATABASE_URL`,
`[migrations].<env>_db_url`, or `[supabase_admin].db_url`. See the
[migrations README](./sql_stuff/migrations/README.md) for the full workflow,
including how to add a migration and how to adopt the runner on an existing
database.

## Versioning & releases

Versioning is driven by [Conventional Commits](https://www.conventionalcommits.org/)
at the merge-to-`main` boundary, using [commitizen](https://commitizen-tools.github.io/commitizen/).

- **Pull request titles must be conventional commits** (`type(scope): summary`,
  e.g. `feat(grid): add column filters`; append `!` or a `BREAKING CHANGE:`
  footer for a breaking change). The `PR Title` check enforces this, and because
  PRs are **squash-merged**, the title becomes the single commit on `main`.
- **On merge to `main`**, the `Release` workflow runs commitizen to bump
  `[project].version`, update `CHANGELOG.md`, tag `vX.Y.Z`, and cut a GitHub
  Release. `fix:` bumps the patch, `feat:` the minor, and a breaking change the
  minor while the project is pre-1.0 (`major_version_zero`). Titles like
  `chore:`/`docs:` produce no release.

Preview the next bump locally without writing anything:

```bash
uv run cz bump --dry-run
```
