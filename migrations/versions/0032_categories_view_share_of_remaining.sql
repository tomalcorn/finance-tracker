-- 0032_categories_view_share_of_remaining
--
-- A pot's `split` becomes its share of the One-offs tracker's **remaining**
-- rather than of the tracker's whole budget (#262). The grid labels it "Share
-- of Remaining": of what is still left to allocate this month, how much is this
-- pot claiming — rather than "of the whole monthly allowance, how much is this".
--
-- Only pot children move. The rule branches on the child's **own** accrual, not
-- on which parent it hangs off, so an ordinary monthly subcategory (Bills,
-- Wants, …) keeps dividing by its parent's `budget` exactly as before. Roots are
-- untouched too: a root still divides by the income allocated to it.
--
-- GETTING THE PARENT'S `remaining` ONTO A CHILD ROW. `remaining` is derived per
-- row in the final SELECT, from that row's own `accrued` and `budget`, so the
-- `base` CTE — which only ever joined `parent.budget` — cannot reach it. The
-- parent's roll-up is therefore recomputed alongside the child's: its own
-- month's payments (`parent_own`) plus its children's (`siblings`, the child
-- itself included, which is what the parent row totals too). A second pass over
-- `base` keyed by parent id would do as well; this way the arithmetic sits next
-- to the joins it comes from. Path A — these are personal-finance-sized tables,
-- and the extra join is over the same two tables `base` already reads.
--
-- The parent's monthly formula (`budget - accrued`) is the only one that can
-- apply: a parent is always a root, and a root may not accrue across months
-- (`MultiMonthRootCategoryError`), so the pot branch of `remaining` is
-- unreachable for it.
--
-- REMAINING ≤ 0 READS AS 0%, matching every other denominator guard in this
-- view. Once the tracker is fully allocated there is no share left to take, and
-- a fully-claimed bar is what `progress` already shows for that state. It also
-- keeps `split` non-negative, which `CategoryView.split` requires — dividing by
-- a negative remaining would emit a negative percentage and fail the read.
--
-- Column order and names are preserved exactly, so this stays a CREATE OR
-- REPLACE and the view keeps its grants. Note the ninth column is `accrued`,
-- per 0031: 0029's text still says `current_month` because that is what it
-- emitted at the time, and re-running it now would fail.
--
-- Idempotent: CREATE OR REPLACE VIEW, so a repeated apply is a no-op.

CREATE OR REPLACE VIEW categories_view WITH (security_invoker = on) AS
WITH own_spend AS (
    SELECT
        p.category_id,
        COALESCE(
            SUM(p.expense - p.income) FILTER (
                WHERE p.payment_date >= date_trunc('month', CURRENT_DATE)
                  AND p.payment_date <  date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
            ),
            0
        ) AS this_month,
        COALESCE(SUM(p.expense - p.income), 0) AS all_time
    FROM payments p
    WHERE p.category_id IS NOT NULL
    GROUP BY p.category_id
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
            THEN c.starting_balance + COALESCE(own.all_time, 0)
            ELSE COALESCE(own.this_month, 0)
        END
        -- Children only ever roll up their monthly figure, and only a monthly
        -- category can have children at all.
        + COALESCE(children.spend, 0) AS accrued,
        parent.budget AS parent_budget,
        -- What the parent row's own `remaining` cell will read: its budget less
        -- the same roll-up it totals for itself. NULL on a root, which has no
        -- parent — and no use for this either.
        parent.budget
            - (COALESCE(parent_own.this_month, 0) + COALESCE(siblings.spend, 0))
            AS parent_remaining,
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
    LEFT JOIN own_spend parent_own ON parent_own.category_id = c.parent_id
    -- The parent's children — this row among them. On a root `c.parent_id` is
    -- NULL, which matches nothing, so the sum is 0 and `parent_remaining` is
    -- NULL by way of `parent.budget`.
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(sibling_spend.this_month), 0) AS spend
        FROM categories sibling
        LEFT JOIN own_spend sibling_spend ON sibling_spend.category_id = sibling.id
        WHERE sibling.parent_id = c.parent_id
    ) siblings ON TRUE
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
    base.accrued,
    CASE
        WHEN base.accrual = 'multi_month'
        THEN base.cost - base.accrued
        ELSE base.budget - base.accrued
    END AS remaining,
    CASE
        WHEN base.accrual = 'multi_month' THEN
            CASE
                WHEN base.cost > 0
                THEN base.accrued / base.cost * 100
                ELSE 0
            END
        ELSE
            CASE
                WHEN base.budget > 0
                THEN base.accrued / base.budget * 100
                ELSE 0
            END
    END AS progress,
    CASE
        WHEN base.parent_id IS NOT NULL THEN
            CASE
                -- A pot: share of what the tracker has left to allocate.
                WHEN base.accrual = 'multi_month' THEN
                    CASE
                        WHEN COALESCE(base.parent_remaining, 0) > 0
                        THEN base.budget / base.parent_remaining * 100
                        ELSE 0
                    END
                -- An ordinary monthly subcategory: unchanged, share of the
                -- parent's budget.
                ELSE
                    CASE
                        WHEN COALESCE(base.parent_budget, 0) > 0
                        THEN base.budget / base.parent_budget * 100
                        ELSE 0
                    END
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
