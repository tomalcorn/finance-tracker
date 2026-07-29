-- 0016_user_settings_rls
--
-- Row-level security for user_settings, the table added in 0015.
--
-- The same joint-aware shape every owned table carries (see
-- versions/prod/0005_enable_rls.sql): a row is admitted when it is the caller's
-- own personal row, or a joint row for an account the caller belongs to. USING
-- and WITH CHECK are identical, so either member can change the joint account's
-- setting — the figure it drives is shared, so the control over it is too.
--
-- This policy is also what makes the settings lookup inside income_sources_view
-- safe: the view is security_invoker, so the lateral join runs under the
-- caller's own policies and can only reach the settings rows they may read.
--
-- prod-only (versions/prod/): the test database runs without RLS and grants the
-- API roles directly (versions/testing/0004), whose ALTER DEFAULT PRIVILEGES
-- already covers tables created later, so no testing overlay is needed here.
--
-- DROP POLICY IF EXISTS before CREATE keeps a repeated apply safe.

ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_settings_user_policy ON user_settings;
CREATE POLICY user_settings_user_policy ON user_settings
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
