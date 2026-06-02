-- Drop all tables and views so the schema can be recreated cleanly.
-- Run this first, then run create_tables.sql, then enable_rls.sql.

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

-- Drop the legacy users table (no longer used)
DROP TABLE IF EXISTS users CASCADE;
