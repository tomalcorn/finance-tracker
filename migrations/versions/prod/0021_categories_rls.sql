-- 0021_categories_rls
--
-- Row-level security for the `categories` table created in 0020, mirroring the
-- joint-aware policy every other owned table carries (prod/0005). Without it
-- the table is exposed: 0020 copies real budget rows into it, and a table with
-- RLS disabled is readable and writable by any `authenticated` role through
-- PostgREST — the app not reading it yet is not protection.
--
-- The policy is the same shape as the others: a row is admitted when it is the
-- caller's own personal row, or a joint row for an account they belong to.
-- Writes on joint rows are fully shared, so USING and WITH CHECK are identical.
--
-- The tree adds no new visibility rule. A child carries the same user_id /
-- ownership_type / joint_account_id as its root, so a category is admitted on
-- its own columns and never needs to consult its parent — which also keeps the
-- policy free of a self-referential subquery on `categories`.
--
-- Prod-only (versions/prod/), like 0005: the test database is RLS-free and
-- relies on the grants in versions/testing/0004 instead. Numbered from the
-- shared sequence, so 0021 is unused by any shared file.

ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS categories_user_policy ON categories;
CREATE POLICY categories_user_policy ON categories
    FOR ALL
    TO authenticated
    USING (
        (ownership_type = 'personal' AND user_id = public.user_id())
        OR (ownership_type = 'joint' AND joint_account_id IN (
            SELECT joint_account_id FROM joint_account_members
            WHERE user_id = public.user_id()
        ))
    )
    WITH CHECK (
        (ownership_type = 'personal' AND user_id = public.user_id())
        OR (ownership_type = 'joint' AND joint_account_id IN (
            SELECT joint_account_id FROM joint_account_members
            WHERE user_id = public.user_id()
        ))
    );
