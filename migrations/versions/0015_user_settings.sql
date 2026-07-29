-- 0015_user_settings
--
-- Per-user preferences, and the first one: which month an income source rolls
-- its payments up over.
--
-- Until now `income_sources_view.current_month` was fixed to the calendar month
-- containing CURRENT_DATE. For anyone paid at the end of the month, that money
-- is what the *next* month is budgeted from, so the budget tracker's `split` —
-- each tracker's budget as a share of the income feeding it — read as 0 until
-- the pay landed. Setting the period to 'previous_month' shifts the income
-- window back one month while leaving the expense side on the current month, so
-- this month's budget is split against last month's pay.
--
-- Scope of a settings row follows the ownership dimension every other owned
-- aggregate carries, because the two halves are configured independently:
--
--   * personal — one row per user (unique on user_id).
--   * joint    — one row per joint *account*, not per member (unique on
--                joint_account_id). The view is shared, so a per-member setting
--                would make the same joint income source read differently for
--                each of them.
--
-- No view of its own: a settings row has no computed columns, so reads hit the
-- table directly (like payments, quick_buttons, and the joint tables).
--
-- Every existing scope is backfilled with a row at the default, so a settings
-- row is something that always exists rather than something a first edit brings
-- into existence. The app seeds one for every scope created afterwards.
--
-- Statements are idempotent (CREATE TABLE IF NOT EXISTS / DROP ... IF EXISTS
-- before ADD / CREATE OR REPLACE VIEW / guarded INSERT) so a partial or
-- repeated apply is safe.

CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    -- Carried because every entity is a FinanceTrackerBaseModel and writes its
    -- whole model, `name` included. A settings row is not a named thing, so it
    -- is written empty and never displayed.
    name TEXT NOT NULL DEFAULT '',
    income_roll_up_period TEXT NOT NULL DEFAULT 'current_month',
    ownership_type TEXT NOT NULL DEFAULT 'personal',
    joint_account_id UUID REFERENCES joint_accounts(id),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Same ownership invariant as every other owned table (0003): a joint row must
-- name the account it belongs to.
ALTER TABLE user_settings DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE user_settings ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

-- The view below reads this column as a period name; an unknown value would
-- silently fall back to the current month, so reject it at the door.
ALTER TABLE user_settings DROP CONSTRAINT IF EXISTS income_roll_up_period_known;
ALTER TABLE user_settings ADD CONSTRAINT income_roll_up_period_known
    CHECK (income_roll_up_period IN ('current_month', 'previous_month'));

-- One settings row per configurable scope, in the shape 0008 uses for budget
-- trackers: partial unique indexes, because what a row is unique *by* differs
-- between the two ownership types. This is what stops a second browser tab from
-- creating a rival row that the view would then pick between arbitrarily.
DROP INDEX IF EXISTS user_settings_personal_user_unique;
CREATE UNIQUE INDEX user_settings_personal_user_unique
    ON user_settings (user_id)
    WHERE ownership_type = 'personal';

DROP INDEX IF EXISTS user_settings_joint_account_unique;
CREATE UNIQUE INDEX user_settings_joint_account_unique
    ON user_settings (joint_account_id)
    WHERE ownership_type = 'joint';

-- Backfill one row per existing scope, at the default. `income_roll_up_period`
-- is left to the column default deliberately: the backfill's job is to make the
-- default explicit, not to choose anything, so every row it writes says exactly
-- what a missing row would have said and no figure moves.
--
-- Both statements are guarded by NOT EXISTS and carry a bare ON CONFLICT DO
-- NOTHING — no conflict target, so it covers the partial unique indexes above,
-- which an inferred target cannot. Re-applying, or applying after the app has
-- already seeded a scope, changes nothing.
--
-- There is no users table: the roster is the distinct owners of personal budget
-- tracker rows, which workspace initialisation has created for every user who
-- has ever logged in.
INSERT INTO user_settings (id, user_id, ownership_type)
SELECT gen_random_uuid(), owners.user_id, 'personal'
FROM (
    SELECT DISTINCT user_id
    FROM budget_tracker
    WHERE ownership_type = 'personal'
) owners
WHERE NOT EXISTS (
    SELECT 1 FROM user_settings us
    WHERE us.ownership_type = 'personal'
      AND us.user_id = owners.user_id
)
ON CONFLICT DO NOTHING;

-- The joint row belongs to the *account*; `user_id` on it is only ever the
-- member who stamped it, so any member will do — the earliest, for determinism.
-- An account with no members is skipped rather than inserting a NULL user_id.
INSERT INTO user_settings (id, user_id, ownership_type, joint_account_id)
SELECT
    gen_random_uuid(),
    (
        SELECT m.user_id
        FROM joint_account_members m
        WHERE m.joint_account_id = ja.id
        ORDER BY m._created_at, m.id
        LIMIT 1
    ),
    'joint',
    ja.id
FROM joint_accounts ja
WHERE EXISTS (
    SELECT 1 FROM joint_account_members m WHERE m.joint_account_id = ja.id
)
AND NOT EXISTS (
    SELECT 1 FROM user_settings us
    WHERE us.ownership_type = 'joint'
      AND us.joint_account_id = ja.id
)
ON CONFLICT DO NOTHING;

-- Replace income_sources_view so its month window is the configured one.
--
-- The existing columns keep their names, types, and order — CREATE OR REPLACE
-- VIEW allows only *trailing* additions, and budget_tracker_view depends on
-- this view's `current_month`. `income_roll_up_period` is appended so a reader
-- can tell which window produced the number without a second query.
--
-- A scope with no settings row falls through the LEFT JOIN as NULL and is
-- COALESCEd to 'current_month'. The backfill above means that is rare rather
-- than universal, but it must stay: a joint account created after this ran has
-- no row until its next login seeds one. Either way the figure is the same, so
-- this migration changes nothing.
CREATE OR REPLACE VIEW income_sources_view WITH (security_invoker = on) AS
SELECT
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    COALESCE(SUM(payments.income), 0) AS current_month,
    "income_sources".budget_tracker_ids,
    "income_sources".ownership_type,
    "income_sources".joint_account_id,
    COALESCE(settings.income_roll_up_period, 'current_month')
        AS income_roll_up_period
FROM
    "income_sources"
-- The settings row governing this income source: the owner's own for a personal
-- source, the account's for a joint one. The view is security_invoker, so this
-- reads under the caller's RLS — a member can read their account's row, and
-- nobody can read anyone else's personal one.
LEFT JOIN LATERAL (
    SELECT us.income_roll_up_period
    FROM user_settings us
    WHERE (
        "income_sources".ownership_type = 'personal'
        AND us.ownership_type = 'personal'
        AND us.user_id = "income_sources".user_id
    ) OR (
        "income_sources".ownership_type = 'joint'
        AND us.ownership_type = 'joint'
        AND us.joint_account_id = "income_sources".joint_account_id
    )
    LIMIT 1
) settings ON TRUE
-- The first day of the month the roll-up covers, computed once so the two
-- bounds below cannot drift apart.
LEFT JOIN LATERAL (
    SELECT date_trunc('month', CURRENT_DATE)
        - CASE
            WHEN COALESCE(settings.income_roll_up_period, 'current_month')
                = 'previous_month'
            THEN INTERVAL '1 month'
            ELSE INTERVAL '0 month'
        END AS starts_on
) roll_up ON TRUE
LEFT JOIN
    payments
ON
    "income_sources".id = payments.income_source_id
    AND payments.payment_date >= roll_up.starts_on
    AND payments.payment_date < roll_up.starts_on + INTERVAL '1 month'
GROUP BY
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    "income_sources".ownership_type,
    "income_sources".joint_account_id,
    "income_sources".budget_tracker_ids,
    settings.income_roll_up_period;
