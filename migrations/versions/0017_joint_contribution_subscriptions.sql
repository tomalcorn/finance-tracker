-- 0017_joint_contribution_subscriptions
--
-- A standing order into the joint account (#205). Contributing is a one-off act
-- today (the Contribute button, #200): it books a personal expense and a
-- matching joint income, once. Most contributions are standing orders, and a
-- plain subscription cannot express one — reconcile only ever creates the
-- personal expense leg, so a subscription pointed at the hidden "Joint" expense
-- source would drain the personal side every month while the joint side never
-- saw the money arrive.
--
-- `joint_income_source_id` is the marker: non-null means "this subscription is a
-- joint contribution", and it names the joint income source the income leg is
-- booked against. The alternative — inferring it from `expense_source_id`
-- pointing at the hidden "Joint" source — was rejected because the income leg
-- must carry an income source of its own (#200) and inference gives that
-- nowhere to live. With the explicit column, `expense_source_id` is *derived* on
-- create (always the hidden "Joint" source) rather than chosen.
--
-- `joint_bank_account_id` is the other half the income leg cannot be written
-- without: a payment needs a bank account, and the contribution's destination is
-- a joint one, so the personal `bank_account_id` (the account the money leaves)
-- cannot serve. Both columns are therefore set together or not at all, which is
-- what `joint_contribution_is_complete` enforces.
--
-- `joint_contribution_is_personal` keeps the pair one-directional. Only the
-- PERSONAL reconcile instance books contributions; a joint-owned subscription
-- that claimed to be one would spawn a joint expense with no counterpart, so it
-- is rejected at the table. This mirrors the domain's own validator, the same
-- defense-in-depth as `ownership_requires_account` (0003).
--
-- The two columns reference the same `income_sources` / `bank_accounts` tables
-- the personal columns do — the joint half of them — so no new table is needed
-- to point at.
--
-- Statements are idempotent (ADD COLUMN IF NOT EXISTS, DROP CONSTRAINT IF
-- EXISTS before ADD, CREATE OR REPLACE VIEW).

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS joint_income_source_id UUID REFERENCES income_sources(id);
ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS joint_bank_account_id UUID REFERENCES bank_accounts(id);

ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS joint_contribution_is_complete;
ALTER TABLE subscriptions ADD CONSTRAINT joint_contribution_is_complete
    CHECK ((joint_income_source_id IS NULL) = (joint_bank_account_id IS NULL));

ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS joint_contribution_is_personal;
ALTER TABLE subscriptions ADD CONSTRAINT joint_contribution_is_personal
    CHECK (joint_income_source_id IS NULL OR ownership_type = 'personal');

-- Surface the two columns on the view the read model validates. As in 0006, the
-- existing columns are listed explicitly and unchanged (CREATE OR REPLACE VIEW
-- only allows appending) and the new ones go at the END, after the ownership
-- pair 0006 appended. Replacing in place preserves the view's grants.
CREATE OR REPLACE VIEW subscriptions_view WITH (security_invoker = on) AS
SELECT
    s.id,
    s.user_id,
    s.name,
    s.amount,
    s.cadence,
    s.bank_account_id,
    s.expense_source_id,
    s.start_date,
    s.end_date,
    s.is_active,
    s._created_at,
    CASE s.cadence
        WHEN 'weekly' THEN s.amount * 52.0 / 12.0
        WHEN 'biannually' THEN s.amount / 6.0
        WHEN 'monthly' THEN s.amount
        WHEN 'quarterly' THEN s.amount / 3.0
        WHEN 'yearly' THEN s.amount / 12.0
        ELSE 0
    END AS monthly_cost,
    s.ownership_type,
    s.joint_account_id,
    s.joint_income_source_id,
    s.joint_bank_account_id
FROM subscriptions s;
