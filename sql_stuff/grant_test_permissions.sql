-- Grant table privileges to the API roles for the TEST database.
-- Needed because the integration tests connect with the anon key, and freshly
-- recreated tables have no privileges for the anon/authenticated roles.
-- Run this after create_tables.sql (RLS is left disabled for the test DB).

GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public
    TO anon, authenticated;

-- Ensure tables created later also get these privileges automatically.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated;
