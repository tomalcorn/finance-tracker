-- Enable Row Level Security (RLS) for all tables and create policies.
--
-- Joint-aware visibility (Joint Workflow epic, T3 / #174): each owned table's
-- policy admits a row when it is the user's own personal row OR a joint row for
-- an account the user belongs to. The `personal` branch is byte-identical to
-- the pre-joint policy, so this is a strict superset — existing users see
-- exactly their current personal data and nothing personal changes.
--
-- Auth: `public.user_id()` reads the Auth0 `userId` TEXT claim from the minted
-- Supabase JWT. This app does NOT use `auth.uid()` (see authenticator.py).
--
-- Write semantics for joint rows: FULLY SHARED. The joint branch is in both
-- USING (SELECT/UPDATE/DELETE) and WITH CHECK (INSERT/UPDATE), so any member of
-- an account can read and write any joint row for that account.
--
-- Membership check: an inline subquery against joint_account_members, which
-- carries an own-rows-only policy (`user_id = public.user_id()`). Because that
-- policy filters by user_id directly rather than re-reading its own table, the
-- subquery is NOT self-referential and does not recurse — no SECURITY DEFINER
-- helper is needed.
--
-- This is a prod-only migration (versions/prod/): RLS exists on prod but not on
-- the RLS-free test database, so the runner applies it only for --env prod. Each
-- policy is dropped if present before being recreated, so applying it over the
-- personal-only policies a pre-joint database already has replaces them cleanly.

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE income_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE one_offs ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE joint_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE joint_account_members ENABLE ROW LEVEL SECURITY;

-- Read the Auth0 sub (userId claim) from the JWT.
CREATE OR REPLACE FUNCTION public.user_id() RETURNS TEXT AS $$
  SELECT NULLIF(
    current_setting('request.jwt.claims', true)::json->>'userId',
    ''
  )::TEXT;
$$ LANGUAGE sql STABLE;

-- Joint-aware policies on the owned aggregates. The USING and WITH CHECK
-- expressions are identical (fully-shared writes).

DROP POLICY IF EXISTS payments_user_policy ON payments;
CREATE POLICY payments_user_policy ON payments
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

DROP POLICY IF EXISTS bank_accounts_user_policy ON bank_accounts;
CREATE POLICY bank_accounts_user_policy ON bank_accounts
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

DROP POLICY IF EXISTS expense_sources_user_policy ON expense_sources;
CREATE POLICY expense_sources_user_policy ON expense_sources
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

DROP POLICY IF EXISTS income_sources_user_policy ON income_sources;
CREATE POLICY income_sources_user_policy ON income_sources
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

DROP POLICY IF EXISTS budget_tracker_user_policy ON budget_tracker;
CREATE POLICY budget_tracker_user_policy ON budget_tracker
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

DROP POLICY IF EXISTS one_offs_user_policy ON one_offs;
CREATE POLICY one_offs_user_policy ON one_offs
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

DROP POLICY IF EXISTS subscriptions_user_policy ON subscriptions;
CREATE POLICY subscriptions_user_policy ON subscriptions
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

-- joint_accounts: visible to (and writable by) members of the account. At
-- account-creation time no membership row exists yet, so inserting the account
-- itself is handled by a separate privileged flow (a later ticket), not by this
-- member-scoped policy.
DROP POLICY IF EXISTS joint_accounts_member_policy ON joint_accounts;
CREATE POLICY joint_accounts_member_policy ON joint_accounts
    FOR ALL
    TO authenticated
    USING (
        id IN (
            SELECT joint_account_id FROM joint_account_members
            WHERE user_id = public.user_id()
        )
    )
    WITH CHECK (
        id IN (
            SELECT joint_account_id FROM joint_account_members
            WHERE user_id = public.user_id()
        )
    );

-- joint_account_members: own-rows-only. A user sees and writes only their own
-- membership rows (never co-members'). This filters by user_id directly, so it
-- is non-recursive and is the base every joint subquery above resolves against.
-- Adding a partner to an account (a row with someone else's user_id) is a
-- privileged invite flow handled in a later ticket, not by this policy.
DROP POLICY IF EXISTS joint_account_members_self_policy ON joint_account_members;
CREATE POLICY joint_account_members_self_policy ON joint_account_members
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Note: Views inherit RLS from their underlying tables. With security_invoker =
-- on, the aggregating views (bank_accounts_view, expense_sources_view,
-- income_sources_view, budget_tracker_view, one_offs_view) sum across whichever
-- rows the caller's policies admit, so a joint account's totals fold in both
-- members' payments automatically.
