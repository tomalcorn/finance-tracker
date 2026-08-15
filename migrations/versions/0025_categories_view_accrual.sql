-- 0025_categories_view_accrual
--
-- Branch categories_view on the accrual dimension 0024 added (#248).
--
-- The branch is ONLY a payment window:
--
--   * `monthly`     — payments in the current calendar month, as before.
--   * `multi_month` — the pot's starting balance plus payments over all time,
--                     exactly as bank_accounts_view computes current_balance.
--
-- Everything else follows from that. A pot's `current_month` is what is in it,
-- `remaining` is what is left to put in, and `progress` is how full it is.
--
-- One thing here is deliberately NOT how one_offs_view worked: **`remaining` no
-- longer subtracts Planned Spend.** The old view computed
-- `cost - current_month - banked`, where `current_month` was the typed-in
-- pledge, so planning to spend money made the pot read as already emptier.
-- Planned Spend is a plan for the month and nothing decrements it; only the
-- starting balance and real payments move `remaining`.
--
-- `progress` is unchanged in practice: it was `banked / cost`, and it is now
-- `(starting_balance + payments) / cost` — the same figure while the starting
-- balance carries the old `banked` and nothing points at a pot yet, and the
-- right one once #251 lets payments do so.
--
-- A monthly parent rolls up its children's MONTHLY figure, never their all-time
-- one. That is what keeps the One-offs root meaning "put in this month"
-- (£240.83 of £599.68) while each pot under it reads as an all-time total. The
-- two answer different questions and both are correct; 0024's
-- `category_multi_month_is_a_child` is what guarantees a parent is always the
-- monthly one.
--
-- The temporary payment resolution from 0023 is unchanged and still goes in
-- #249 — see the note on that ticket.
--
-- The three new columns are appended at the END of the SELECT, after `split`:
-- CREATE OR REPLACE VIEW can only add columns to the end, never insert them
-- mid-list, and replacing in place is what preserves the view's grants. Same
-- reason 0002 and 0017 append theirs.

CREATE OR REPLACE VIEW categories_view WITH (security_invoker = on) AS
WITH payment_categories AS (
    -- TEMPORARY (see 0023): payments.category_id does not exist until #249, so
    -- a payment is resolved through expense_sources — an ordinary source IS its
    -- category (0020 preserved ids), while a hidden stand-in's payments belong
    -- to the ROOT, which the join to budget_tracker resolves. #249 deletes this.
    SELECT
        COALESCE(bt.id, es.id) AS category_id,
        p.expense - p.income AS net,
        p.payment_date
    FROM payments p
    JOIN expense_sources es ON es.id = p.expense_source_id
    LEFT JOIN budget_tracker bt
        ON bt.id = es.budget_tracker_ids[1]
        AND bt.name = es.name
),
-- Both windows are computed for every category; the outer query picks the one
-- its accrual asks for. Filtering here instead would make the window a property
-- of the CTE, when it is a property of the row.
own_spend AS (
    SELECT
        category_id,
        COALESCE(
            SUM(net) FILTER (
                WHERE payment_date >= date_trunc('month', CURRENT_DATE)
                  AND payment_date <  date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
            ),
            0
        ) AS this_month,
        COALESCE(SUM(net), 0) AS all_time
    FROM payment_categories
    GROUP BY category_id
),
base AS (
    SELECT
        c.id,
        c.user_id,
        c.name,
        c.parent_id,
        c.budget,
        c.accrual,
        c.cost,
        c.starting_balance,
        c.ownership_type,
        c.joint_account_id,
        c._created_at,
        CASE
            WHEN c.accrual = 'multi_month'
            THEN COALESCE(c.starting_balance, 0) + COALESCE(own.all_time, 0)
            ELSE COALESCE(own.this_month, 0)
        END
        -- Children only ever roll up their monthly figure, and only a monthly
        -- category can have children at all.
        + COALESCE(children.spend, 0) AS current_month,
        parent.budget AS parent_budget,
        income_totals.total_income
    FROM categories c
    LEFT JOIN own_spend own ON own.category_id = c.id
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(child_spend.this_month), 0) AS spend
        FROM categories child
        LEFT JOIN own_spend child_spend ON child_spend.category_id = child.id
        WHERE child.parent_id = c.id
    ) children ON TRUE
    LEFT JOIN categories parent ON parent.id = c.parent_id
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(incv.current_month), 0) AS total_income
        FROM income_sources inc
        JOIN income_sources_view incv ON inc.id = incv.id
        WHERE c.id = ANY(inc.budget_tracker_ids)
    ) income_totals ON TRUE
)
SELECT
    base.id,
    base.user_id,
    base.name,
    base.parent_id,
    base.budget,
    base.ownership_type,
    base.joint_account_id,
    base._created_at,
    base.current_month,
    -- A pot measures what is in it against its cost; a monthly category
    -- measures this month's spend against this month's budget.
    CASE
        WHEN base.accrual = 'multi_month'
        THEN base.cost - base.current_month
        ELSE base.budget - base.current_month
    END AS remaining,
    CASE
        WHEN base.accrual = 'multi_month' THEN
            CASE
                WHEN COALESCE(base.cost, 0) > 0
                THEN base.current_month / base.cost * 100
                ELSE 0
            END
        ELSE
            CASE
                WHEN base.budget > 0
                THEN base.current_month / base.budget * 100
                ELSE 0
            END
    END AS progress,
    -- Unchanged: a child's share is of its parent's budget, a root's of total
    -- income. A pot's `budget` is its Planned Spend, so its share still reads
    -- as "how much of this month's one-offs allowance is going here" — exactly
    -- what one_offs_view.split meant.
    CASE
        WHEN base.parent_id IS NOT NULL THEN
            CASE
                WHEN COALESCE(base.parent_budget, 0) > 0
                THEN base.budget / base.parent_budget * 100
                ELSE 0
            END
        ELSE
            CASE
                WHEN COALESCE(base.total_income, 0) > 0
                THEN base.budget / base.total_income * 100
                ELSE 0
            END
    END AS split,
    base.accrual,
    base.cost,
    base.starting_balance
FROM base;
