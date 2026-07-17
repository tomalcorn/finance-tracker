# Database migrations

Standalone, versioned SQL migrations for the finance-tracker Postgres database
(Supabase). This package lives outside `src/` because it is ops tooling, not
part of the app.

The runner applies each `versions/NNNN_description.sql` file in order and
records what it has applied in a `schema_migrations` table, so re-running only
applies files that have not yet run. Each file runs inside its own transaction,
so a failed file rolls back cleanly and records nothing.

```text
migrations/
  cli.py         # pydantic-settings CLI app + per-env URL selection
  discovery.py   # pure ordering / filename rules
  runner.py      # applies files, maintains schema_migrations
  versions/      # shared .sql files, applied to every environment
    prod/        # prod-only overlay (RLS policies)
    testing/     # testing-only overlay (role grants)
```

**Per-environment overlays.** Files directly in `versions/` are *shared* and
apply to every environment. Files in `versions/prod/` or `versions/testing/`
apply **only** when `--env` selects that environment, so a difference that must
exist in one database but not the other (production RLS; the test database's
role grants) still lives in a versioned, runner-applied file. Recreating a
database from scratch is therefore just the runner: `--env prod` replays the
shared files plus the prod overlay, `--env testing` the shared files plus the
testing overlay. Shared files and an overlay share **one** version sequence
(pick the next unused `NNNN` across both), so a reused number fails discovery
loudly rather than one file silently shadowing another.

The runner and its dependencies (`psycopg`, `pydantic-settings`) are **dev
dependencies** — install them with `uv sync` (the default dev groups).

## Commands

Run from the repo root:

```bash
uv run poe migrate                   # apply all pending migrations
uv run poe migrate --dry-run         # list what apply would do, change nothing
uv run poe migrate --baseline --dry-run  # list what baseline would record
uv run poe migrate --status          # list applied / pending, change nothing
uv run poe migrate --baseline        # record present files as applied, run none
uv run poe migrate --help            # full flag list
```

`--dry-run` is a preview modifier: on its own it previews `apply`, and combined
with `--baseline` it previews baselining. `--status` is standalone and cannot be
combined with `--baseline` or `--dry-run`.

## Connecting to the database

The runner needs a **direct Postgres connection string** — the app itself only
talks to Supabase over PostgREST, which cannot run DDL. Testing and prod are
**separate databases** with different connection strings, so the CLI keeps one
URL per environment and `--env` selects between them:

| `--env`   | URL read from       |
| --------- | ------------------- |
| `testing` | `TEST_DATABASE_URL` |
| `prod`    | `DATABASE_URL`      |

`--env` defaults to `testing`. Each URL is read from the environment, or from a
`.env` file at the repo root (the environment wins). The URLs are deliberately
**not** exposed as CLI flags, to keep connection strings off the command line.
If the selected environment has no URL configured, the CLI exits with a clear
error rather than connecting to the wrong place.

```bash
# .env at the repo root:
#   DATABASE_URL=postgresql://postgres:<pw>@<prod-host>:5432/postgres
#   TEST_DATABASE_URL=postgresql://postgres:<pw>@<test-host>:5432/postgres

uv run poe migrate --status                 # targets testing (the default)
uv run poe migrate --env prod --status      # targets prod
```

Find each connection string in that project's Supabase dashboard under
**Project Settings → Database → Connection string**.

## Adding a migration

1. Create the next file: `versions/NNNN_short_description.sql` (4-digit version,
   one higher than the latest; `lower_snake_case` name). For example, changing a
   view — the case that motivated this runner (#156) — becomes a new file with a
   `CREATE OR REPLACE VIEW ...` statement. For a change that must apply to only
   one environment, put it in `versions/prod/` or `versions/testing/` instead and
   number it from the same shared sequence (the next unused `NNNN`).
2. Write plain SQL. Prefer idempotent statements (`CREATE OR REPLACE VIEW`,
   `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) where practical.
3. Apply it with `uv run poe migrate` against testing (the default), then
   `uv run poe migrate --env prod`.

## Adopting on an existing database

The tables and views in `versions/0001_initial_schema.sql` already exist on the
live databases, so running `0001` there would fail. On each existing database,
run once:

```bash
uv run poe migrate --baseline
```

This records every present migration as applied **without executing it**. New
migrations added afterwards apply normally.

## What is and isn't a migration

`versions/0001_initial_schema.sql` is the structural baseline: tables, foreign
keys, and views. The two environment-specific setup steps that used to live
outside the runner are now versioned overlays (see **Per-environment overlays**
above), so the whole database — shared schema plus its environment's specifics —
is reproducible from the runner alone:

- `versions/prod/0005_enable_rls.sql` — production row-level security policies.
- `versions/testing/0004_grant_test_permissions.sql` — role grants for the
  RLS-free test database.

The runner only rolls forward — there is no down/teardown step. To rebuild a
database from scratch, drop it (or its `public` schema) through Supabase or
`psql`, then re-run `uv run poe migrate --env <env>`.
