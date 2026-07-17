-- Drop all tables and views so the schema can be recreated cleanly.
-- Manual teardown helper: run this, then rebuild from the migration runner
-- (`uv run poe migrate --env <env>`), which recreates the schema, RLS, and
-- grants for that environment.

-- Drop views first (CASCADE on tables also removes them, but be explicit)
DROP VIEW IF EXISTS bank_accounts_view CASCADE;
DROP VIEW IF EXISTS budget_tracker_view CASCADE;
DROP VIEW IF EXISTS income_sources_view CASCADE;
DROP VIEW IF EXISTS expense_sources_view CASCADE;
DROP VIEW IF EXISTS one_offs_view CASCADE;
DROP VIEW IF EXISTS subscriptions_view CASCADE;

-- Drop tables (CASCADE clears foreign keys between them)
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS one_offs CASCADE;
DROP TABLE IF EXISTS budget_tracker CASCADE;
DROP TABLE IF EXISTS income_sources CASCADE;
DROP TABLE IF EXISTS expense_sources CASCADE;
DROP TABLE IF EXISTS bank_accounts CASCADE;

-- Drop the joint tables (added in 0002); members references accounts.
DROP TABLE IF EXISTS joint_account_members CASCADE;
DROP TABLE IF EXISTS joint_accounts CASCADE;

-- Drop the schema_migrations tracking table so the runner replays from scratch.
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- Drop the legacy users table (no longer used)
DROP TABLE IF EXISTS users CASCADE;
