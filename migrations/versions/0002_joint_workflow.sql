-- 0002_joint_workflow
--
-- Schema baseline for the Joint Workflow epic: the two joint tables, the
-- ownership dimension (ownership_type / joint_account_id) on every owned
-- aggregate, and a payments self-reference for transfer traceability (T7).
--
-- Statements are idempotent (CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT
-- EXISTS / CREATE OR REPLACE VIEW) so a partial or repeated apply is safe.
--
-- RLS is NOT part of this migration. The computed views use
-- security_invoker = on, so joint visibility for the *other* member's rows is a
-- row-level-security concern applied per environment from sql_stuff/, not here.
--
-- View review (see below): the aggregating views group by each aggregate's own
-- primary key, so every visible payment on a shared bank_account/source id folds
-- into the one owning row regardless of which member made it — the SUMs are
-- already correct for joint. The views are replaced here only to surface the new
-- ownership columns to the read models, not to fix aggregation.

CREATE TABLE IF NOT EXISTS joint_accounts (
    id UUID PRIMARY KEY,
    name TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- user_id is the Auth0 sub (TEXT), matching the user_id columns elsewhere.
CREATE TABLE IF NOT EXISTS joint_account_members (
    id UUID PRIMARY KEY,
    joint_account_id UUID NOT NULL REFERENCES joint_accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    UNIQUE (joint_account_id, user_id)
);

-- Ownership dimension on every owned aggregate. subscriptions is included
-- (beyond the entities that back the joint page's other blocks) so a joint
-- subscription can be modelled and its writes carry the columns.
ALTER TABLE payments        ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE payments        ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE bank_accounts   ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE bank_accounts   ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE expense_sources ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE expense_sources ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE income_sources  ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE income_sources  ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE budget_tracker  ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE budget_tracker  ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE one_offs        ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE one_offs        ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);
ALTER TABLE subscriptions   ADD COLUMN IF NOT EXISTS ownership_type   TEXT NOT NULL DEFAULT 'personal';
ALTER TABLE subscriptions   ADD COLUMN IF NOT EXISTS joint_account_id UUID REFERENCES joint_accounts(id);

-- Transfer traceability (T7): a payment can point at the payment it settles.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS linked_payment_id UUID REFERENCES payments(id);

-- Replace the views so the ownership columns reach the read models. The
-- aggregation semantics are unchanged: each view groups by the aggregate's own
-- primary key, so ownership_type / joint_account_id are functionally determined
-- by the group and add no new grouping granularity.

CREATE OR REPLACE VIEW bank_accounts_view WITH (security_invoker = on) AS
SELECT
    ba.id,
    ba.user_id,
    ba.name,
    ba.ownership_type,
    ba.joint_account_id,
    ba.starting_balance,
    ba._created_at,
    ba.starting_balance + COALESCE(SUM(p.income - p.expense), 0) AS current_balance
FROM
    bank_accounts ba
LEFT JOIN
    payments p
ON
    ba.id = p.bank_account_id
    AND p.payment_date <= CURRENT_DATE
GROUP BY
    ba.id,
    ba.user_id,
    ba.name,
    ba.ownership_type,
    ba.joint_account_id,
    ba.starting_balance,
    ba._created_at;

CREATE OR REPLACE VIEW expense_sources_view WITH (security_invoker = on) AS
SELECT
    es.id,
    es.user_id,
    es.name,
    es.ownership_type,
    es.joint_account_id,
    es.budget,
    COALESCE(SUM(p.expense - p.income), 0) AS current_month,
    es.budget_tracker_ids,
    es._created_at,
    es.budget - COALESCE(SUM(p.expense - p.income), 0) AS remaining,
    CASE
        WHEN es.budget > 0
        THEN COALESCE(SUM(p.expense - p.income), 0) / es.budget * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(bt_totals.total_budget, 0) > 0
        THEN es.budget / bt_totals.total_budget * 100
        ELSE 0
    END AS split
FROM
    expense_sources es
LEFT JOIN
    payments p
ON
    es.id = p.expense_source_id
    AND p.payment_date >= date_trunc('month', CURRENT_DATE)
    AND p.payment_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM budget_tracker bt
    WHERE bt.id = ANY(es.budget_tracker_ids)
) bt_totals ON TRUE
GROUP BY
    es.id, es.user_id, es.name, es.ownership_type, es.joint_account_id,
    es.budget, es.budget_tracker_ids, es._created_at, bt_totals.total_budget;

CREATE OR REPLACE VIEW income_sources_view WITH (security_invoker = on) AS
SELECT
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    "income_sources".ownership_type,
    "income_sources".joint_account_id,
    COALESCE(SUM(payments.income), 0) AS current_month,
    "income_sources".budget_tracker_ids
FROM
    "income_sources"
LEFT JOIN
    payments
ON
    "income_sources".id = payments.income_source_id
    AND payments.payment_date >= date_trunc('month', CURRENT_DATE)
    AND payments.payment_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    "income_sources".ownership_type,
    "income_sources".joint_account_id,
    "income_sources".budget_tracker_ids;

CREATE OR REPLACE VIEW budget_tracker_view WITH (security_invoker = on) AS
SELECT
    bt.id,
    bt.user_id,
    bt.name,
    bt.ownership_type,
    bt.joint_account_id,
    bt.total_budget,
    bt._created_at,
    COALESCE(SUM(esv.current_month), 0) AS current_month,
    bt.total_budget - COALESCE(SUM(esv.current_month), 0) AS remaining,
    CASE
        WHEN bt.total_budget > 0
        THEN COALESCE(SUM(esv.current_month), 0) / bt.total_budget * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(income_totals.total_income, 0) > 0
        THEN bt.total_budget / income_totals.total_income * 100
        ELSE 0
    END AS split
FROM
    budget_tracker bt
LEFT JOIN
    expense_sources es ON bt.id = ANY(es.budget_tracker_ids)
LEFT JOIN
    expense_sources_view esv ON es.id = esv.id
LEFT JOIN LATERAL (
    SELECT COALESCE(SUM(incv.current_month), 0) AS total_income
    FROM income_sources inc
    JOIN income_sources_view incv ON inc.id = incv.id
    WHERE bt.id = ANY(inc.budget_tracker_ids)
) income_totals ON TRUE
GROUP BY
    bt.id, bt.user_id, bt.name, bt.ownership_type, bt.joint_account_id,
    bt.total_budget, bt._created_at, income_totals.total_income;

CREATE OR REPLACE VIEW one_offs_view WITH (security_invoker = on) AS
SELECT
    fs.id,
    fs.user_id,
    fs.name,
    fs.ownership_type,
    fs.joint_account_id,
    fs.cost,
    fs.current_month,
    fs.banked,
    fs.budget_tracker_id,
    fs._created_at,
    fs.cost - fs.current_month - fs.banked AS remaining,
    CASE
        WHEN fs.cost > 0
        THEN fs.banked / fs.cost * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(bt_totals.total_budget, 0) > 0
        THEN fs.current_month / bt_totals.total_budget * 100
        ELSE 0
    END AS split
FROM
    one_offs fs
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM budget_tracker bt
    WHERE bt.id = fs.budget_tracker_id
) bt_totals ON TRUE;

-- subscriptions_view selects s.*, so the new subscriptions columns flow through
-- without a replacement here.
