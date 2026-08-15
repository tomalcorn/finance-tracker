-- 0023_categories_view
--
-- One view computing spend/remaining/progress/split at BOTH levels of the
-- category tree (#247, epic #239), replacing what budget_tracker_view and
-- expense_sources_view each computed for their own level.
--
-- The two old views were already the same shape with different inputs: amount
-- (total_budget vs budget), spent (sum of children vs sum of payments),
-- remaining, progress, and a split that divides by total income at the top and
-- by the parent's budget below. With a parent_id both collapse into one
-- definition, which is the whole argument for the merge.
--
-- ADDITIVE, like 0020. budget_tracker_view, expense_sources_view and
-- one_offs_view are untouched and still serve the app; nothing reads this view
-- until the UI cuts over in #250-#252. Landing it alongside them is deliberate:
-- it makes the two computable side by side, so the merge can be *proved*
-- faithful on real data before anything depends on it.
--
-- Depth is capped at two (0020's trigger), so the roll-up is a plain self-join
-- rather than a WITH RECURSIVE.
--
-- The monthly window applies to every category here. Multi-month accrual —
-- one-offs' cost/banked, and the branch that widens this window — is #248.

-- ---------------------------------------------------------------------------
-- TEMPORARY: how a payment finds its category.
--
-- payments.category_id does not exist yet (it is #249), so spend is resolved
-- through expense_sources, which is still present:
--
--   * an ordinary expense source IS its category — 0020 preserved ids, so
--     es.id is already a valid categories.id;
--   * a hidden stand-in ("Joint"/"Savings"/"One-offs" — named after its tracker
--     AND linked to it) has no category of its own, because roots are directly
--     attributable now. Its payments belong to the ROOT, which is what the join
--     to budget_tracker below resolves them to.
--
-- Both conditions together identify a stand-in, so a genuine user category
-- called "Savings" under Expenses resolves to itself.
--
-- This is not cosmetic: on live data 55% of a month's net spend sits on stand-in
-- sources (the Joint contributions above all), so the naive
-- `p.expense_source_id = c.id` join would silently lose most of the money.
--
-- #249 DELETES this CTE and joins payments.category_id directly.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW categories_view WITH (security_invoker = on) AS
WITH payment_categories AS (
    SELECT
        COALESCE(bt.id, es.id) AS category_id,
        p.expense - p.income AS net
    FROM payments p
    JOIN expense_sources es ON es.id = p.expense_source_id
    LEFT JOIN budget_tracker bt
        ON bt.id = es.budget_tracker_ids[1]
        AND bt.name = es.name
    WHERE p.payment_date >= date_trunc('month', CURRENT_DATE)
      AND p.payment_date <  date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
),
own_spend AS (
    SELECT category_id, COALESCE(SUM(net), 0) AS own
    FROM payment_categories
    GROUP BY category_id
),
-- current_month is own payments PLUS the children's, because a parent is
-- directly attributable too (#239). It is not just the sum of the children the
-- way budget_tracker_view's was, and a root holding spend of its own is exactly
-- why its children's `split` no longer sums to 100%.
base AS (
    SELECT
        c.id,
        c.user_id,
        c.name,
        c.parent_id,
        c.budget,
        c.ownership_type,
        c.joint_account_id,
        c._created_at,
        COALESCE(own.own, 0) + COALESCE(children.spend, 0) AS current_month,
        parent.budget AS parent_budget,
        income_totals.total_income
    FROM categories c
    LEFT JOIN own_spend own ON own.category_id = c.id
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(child_spend.own), 0) AS spend
        FROM categories child
        LEFT JOIN own_spend child_spend ON child_spend.category_id = child.id
        WHERE child.parent_id = c.id
    ) children ON TRUE
    LEFT JOIN categories parent ON parent.id = c.parent_id
    -- Income is a root-level notion only: income_sources.budget_tracker_ids
    -- holds root ids (preserved by 0020), so this resolves to 0 for a child and
    -- its split falls to the parent branch below. Reading through
    -- income_sources_view rather than payments keeps the roll-up period from
    -- 0015 in force.
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
    base.budget - base.current_month AS remaining,
    CASE
        WHEN base.budget > 0
        THEN base.current_month / base.budget * 100
        ELSE 0
    END AS progress,
    -- A child's share is of its parent's budget; a root's is of total income.
    -- Same two rules the old views had, now chosen by position in the tree
    -- rather than by which view you happened to be reading.
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
    END AS split
FROM base;
