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
  versions/      # the ordered .sql files
```

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
   `CREATE OR REPLACE VIEW ...` statement.
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
keys, and views. Two things are intentionally **not** migrations, because they
differ per environment and are applied as one-off setup:

- `../sql_stuff/enable_rls.sql` — production row-level security policies.
- `../sql_stuff/grant_test_permissions.sql` — role grants for the RLS-free test
  database.

`../sql_stuff/drop_tables.sql` remains a manual teardown helper.
