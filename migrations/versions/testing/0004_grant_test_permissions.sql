-- Grant table privileges to the API roles for the TEST database.
--
-- Testing-only migration (versions/testing/): the integration tests connect
-- with the anon key against an RLS-free test database, and freshly created
-- tables have no privileges for the anon/authenticated roles. The runner applies
-- this only for --env testing; prod relies on RLS policies instead (see
-- versions/prod/). Statements are idempotent, so a repeated apply is safe.

GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public
    TO anon, authenticated;

-- Ensure tables created later also get these privileges automatically.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated;
