# Database migrations

Ordered, versioned SQL migrations for the finance-tracker Postgres database
(Supabase). The runner applies each `NNNN_description.sql` file in this
directory in order and records what it has applied in a `schema_migrations`
table, so re-running only applies files that have not yet run.

## Commands

Run from the repo root:

```bash
uv run poe migrate            # apply pending migrations to the testing DB
uv run poe migrate --env prod # apply pending migrations to prod
uv run poe migrate --status   # list applied / pending, change nothing
uv run poe migrate --baseline # record all present files as applied, run none
```

## Connecting to the database

The runner needs a **direct Postgres connection string** (the app itself only
talks to Supabase over PostgREST, which cannot run DDL). It is resolved in this
order, first match wins:

1. The `DATABASE_URL` environment variable.
2. `[migrations].<env>_db_url` in `.streamlit/secrets.toml`.
3. `[supabase_admin].db_url` in `.streamlit/secrets.toml`.

Example `.streamlit/secrets.toml` section:

```toml
[migrations]
testing_db_url = "postgresql://postgres:<pw>@<host>:5432/postgres"
prod_db_url    = "postgresql://postgres:<pw>@<host>:5432/postgres"
```

Find the connection string in the Supabase dashboard under
**Project Settings → Database → Connection string**.

## Adding a migration

1. Create the next file: `NNNN_short_description.sql` (4-digit version, one
   higher than the latest; `lower_snake_case` name). For example, changing a
   view — the case that motivated this runner (#156) — becomes a new file with
   the `CREATE OR REPLACE VIEW ...` statement.
2. Write plain SQL. Statements run inside a single transaction per file, so a
   failure rolls the whole file back. Prefer idempotent statements
   (`CREATE OR REPLACE VIEW`, `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT
   EXISTS`) where practical.
3. Apply it with `uv run poe migrate` (testing first, then `--env prod`).

## Adopting on an existing database

The tables and views in `0001_initial_schema.sql` already exist on the live
databases, so running `0001` there would fail. On each existing database, run
once:

```bash
uv run poe migrate --baseline --env prod
```

This records every present migration as applied **without executing it**. New
migrations added afterwards apply normally.

## What is and isn't a migration

`0001_initial_schema.sql` is the structural baseline: tables, foreign keys, and
views. Two things are intentionally **not** migrations, because they differ per
environment and are applied as one-off setup:

- `../enable_rls.sql` — production row-level security policies.
- `../grant_test_permissions.sql` — role grants for the RLS-free test database.

`../drop_tables.sql` remains a manual teardown helper.
