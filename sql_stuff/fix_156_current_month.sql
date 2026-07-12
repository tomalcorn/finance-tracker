-- Fix #156: income_sources_view (and the identical expense_sources_view) summed
-- every payment up to CURRENT_DATE into `current_month`, so prior months leaked
-- into the current-month figure. Scope both to the current calendar month.
--
-- Idempotent — run against the target Supabase database to update the live views.

CREATE OR REPLACE VIEW expense_sources_view WITH (security_invoker = on) AS
SELECT
    es.id,
    es.user_id,
    es.name,
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
    es.id, es.user_id, es.name, es.budget, es.budget_tracker_ids, es._created_at, bt_totals.total_budget;

CREATE OR REPLACE VIEW income_sources_view WITH (security_invoker = on) AS
SELECT
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
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
    "income_sources".budget_tracker_ids;
