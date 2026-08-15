-- 0019_income_sources_view_created_at
--
-- Re-add `_created_at` to income_sources_view.
--
-- Every table carries `_created_at`, and five of the six views select it. This
-- one stopped: 0015 rewrote the view to move its month window and did not carry
-- the column over, because nothing read it at the time.
--
-- Something does now. Grid rows are ordered by `created_at` as their final sort
-- key (#236) — Path A reads are unordered, and a stable sort otherwise preserves
-- whatever order the fetch happened to return, which an UPDATE changes. The read
-- models declare the column as required, so an income-source read fails
-- validation until the view supplies it.
--
-- Appended as the **last** select column on purpose: CREATE OR REPLACE VIEW
-- permits only trailing additions, and budget_tracker_view depends on this
-- view's `current_month`, so the existing columns keep their names, types, and
-- positions. It joins the GROUP BY for the same reason every other
-- income_sources column does — the select list aggregates over payments.
--
-- No data change: the column already exists on the table with a NOT NULL
-- default, so this only widens what the view exposes.

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
        AS income_roll_up_period,
    "income_sources"._created_at
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
    "income_sources"._created_at,
    settings.income_roll_up_period;
