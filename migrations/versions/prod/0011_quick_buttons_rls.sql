-- 0011_quick_buttons_rls
--
-- Row-level security for quick_buttons (#60), the table added in 0010.
--
-- The policy is the same joint-aware shape every owned table carries (see
-- versions/prod/0005_enable_rls.sql): a row is admitted when it is the caller's
-- own personal row, or a joint row for an account the caller belongs to. USING
-- and WITH CHECK are identical, so joint buttons are fully shared — either
-- member can add, edit, or remove one.
--
-- prod-only (versions/prod/): the test database runs without RLS and grants the
-- API roles directly (versions/testing/0004), whose ALTER DEFAULT PRIVILEGES
-- already covers tables created later, so no testing overlay is needed here.
--
-- DROP POLICY IF EXISTS before CREATE keeps a repeated apply safe.

ALTER TABLE quick_buttons ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS quick_buttons_user_policy ON quick_buttons;
CREATE POLICY quick_buttons_user_policy ON quick_buttons
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
