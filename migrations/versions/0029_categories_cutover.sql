-- 0029_categories_cutover
--
-- The cutover (#250, epic #239). After this, `categories` is the only thing the
-- app reads or writes for budgets, and a payment points at a category directly.
--
-- Everything here moves together because the change is indivisible. Switching
-- the grids to write `categories` means a new category has no `expense_sources`
-- row, so `categories_view`'s temporary CTE — which resolved a payment through
-- that table — would silently drop its payments. Deleting the CTE requires the
-- repoint; the repoint requires the FK to have moved. Doing the repoint first
-- instead is no better: it moves payments somewhere `expense_sources_view`
-- cannot see, blanking Joint/Savings/One-offs on the live page.
--
-- The old tables and views are deliberately LEFT IN PLACE, unread, so the
-- cutover stays recoverable. Dropping them is a later ticket.

-- ---------------------------------------------------------------------------
-- 1. Catch any drift since 0028.
--
-- The app has still been writing budget trackers, expense sources and one-offs
-- through the old tables until this deploy, so anything added since 0028 has no
-- category yet. Same statements as 0020/0024, which are safe to repeat:
-- ON CONFLICT (id) DO NOTHING skips what is already migrated, and the accrual
-- UPDATE is guarded on the default so a live pot is left alone.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    offenders INT;
BEGIN
    SELECT COUNT(*) INTO offenders
    FROM expense_sources
    WHERE COALESCE(array_length(budget_tracker_ids, 1), 0) > 1;
    IF offenders > 0 THEN
        RAISE EXCEPTION
            '% expense_sources row(s) link to more than one budget tracker; '
            '0029 will not pick one for you. Resolve them, then re-apply.',
            offenders;
    END IF;

    SELECT COUNT(*) INTO offenders
    FROM expense_sources
    WHERE budget_tracker_ids IS NULL OR array_length(budget_tracker_ids, 1) IS NULL;
    IF offenders > 0 THEN
        RAISE EXCEPTION
            '% expense_sources row(s) link to no budget tracker and have no '
            'parent to migrate under. Link or delete them, then re-apply.',
            offenders;
    END IF;

    SELECT COUNT(*) INTO offenders FROM one_offs WHERE budget_tracker_id IS NULL;
    IF offenders > 0 THEN
        RAISE EXCEPTION
            '% one_offs row(s) link to no budget tracker and have no parent to '
            'migrate under. Link or delete them, then re-apply.', offenders;
    END IF;

    SELECT COUNT(*) INTO offenders
    FROM (
        SELECT name FROM expense_sources
        UNION ALL
        SELECT name FROM one_offs
    ) named
    WHERE named.name IS NULL OR btrim(named.name) = '';
    IF offenders > 0 THEN
        RAISE EXCEPTION
            '% expense_sources/one_offs row(s) have a blank name and cannot '
            'become categories. Name or delete them, then re-apply.', offenders;
    END IF;
END $$;

INSERT INTO categories (
    id, user_id, name, parent_id, budget,
    ownership_type, joint_account_id, _created_at
)
SELECT
    bt.id, bt.user_id, bt.name, NULL, bt.total_budget,
    bt.ownership_type, bt.joint_account_id, bt._created_at
FROM budget_tracker bt
ON CONFLICT (id) DO NOTHING;

INSERT INTO categories (
    id, user_id, name, parent_id, budget,
    ownership_type, joint_account_id, _created_at
)
SELECT
    es.id, es.user_id, es.name, es.budget_tracker_ids[1], es.budget,
    es.ownership_type, es.joint_account_id, es._created_at
FROM expense_sources es
WHERE NOT EXISTS (
    SELECT 1 FROM budget_tracker bt
    WHERE bt.id = es.budget_tracker_ids[1]
      AND bt.name = es.name
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO categories (
    id, user_id, name, parent_id, budget,
    ownership_type, joint_account_id, _created_at
)
SELECT
    oo.id, oo.user_id, oo.name, oo.budget_tracker_id, 0,
    oo.ownership_type, oo.joint_account_id, oo._created_at
FROM one_offs oo
ON CONFLICT (id) DO NOTHING;

UPDATE categories c
SET accrual          = 'multi_month',
    cost             = COALESCE(oo.cost, 0),
    starting_balance = COALESCE(oo.banked, 0),
    budget           = COALESCE(oo.current_month, 0)
FROM one_offs oo
WHERE oo.id = c.id
  AND c.accrual = 'monthly';

-- ---------------------------------------------------------------------------
-- 2. Repoint the stand-ins.
--
-- A hidden stand-in existed only to be attributable on its tracker's behalf,
-- and was never migrated (0020), so its id names no category. Its rows belong
-- to the ROOT — which is now attributable itself.
--
-- A stand-in is both conditions together, as everywhere else: named after a
-- root AND linked to the tracker of that name. A genuine user category called
-- "Savings" under Expenses is untouched.
--
-- The four `Bank:` payments are NOT special-cased onto their pots. That money
-- is already inside each pot's `starting_balance` (0024), so attributing the
-- payments as well would count it twice.
--
-- The old foreign keys come off FIRST. They still point at `expense_sources`,
-- and a root id is not in that table, so the repoint would violate the very
-- constraint it is moving away from. Dropping them here rather than in step 3
-- is what makes the update possible at all.
-- ---------------------------------------------------------------------------
ALTER TABLE payments       DROP CONSTRAINT IF EXISTS payments_category_id_fkey;
ALTER TABLE subscriptions  DROP CONSTRAINT IF EXISTS subscriptions_category_id_fkey;
ALTER TABLE quick_buttons  DROP CONSTRAINT IF EXISTS quick_buttons_category_id_fkey;

UPDATE payments p
SET category_id = es.budget_tracker_ids[1]
FROM expense_sources es
WHERE es.id = p.category_id
  AND EXISTS (
      SELECT 1 FROM budget_tracker bt
      WHERE bt.id = es.budget_tracker_ids[1]
        AND bt.name = es.name
  );

UPDATE subscriptions s
SET category_id = es.budget_tracker_ids[1]
FROM expense_sources es
WHERE es.id = s.category_id
  AND EXISTS (
      SELECT 1 FROM budget_tracker bt
      WHERE bt.id = es.budget_tracker_ids[1]
        AND bt.name = es.name
  );

UPDATE quick_buttons q
SET category_id = es.budget_tracker_ids[1]
FROM expense_sources es
WHERE es.id = q.category_id
  AND EXISTS (
      SELECT 1 FROM budget_tracker bt
      WHERE bt.id = es.budget_tracker_ids[1]
        AND bt.name = es.name
  );

-- Nothing may be left pointing outside `categories`, or the constraints below
-- would fail with a bare 23503 naming neither the row nor the reason.
DO $$
DECLARE
    orphans INT;
BEGIN
    SELECT
        (SELECT COUNT(*) FROM payments p
          WHERE p.category_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM categories c WHERE c.id = p.category_id))
      + (SELECT COUNT(*) FROM subscriptions s
          WHERE s.category_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM categories c WHERE c.id = s.category_id))
      + (SELECT COUNT(*) FROM quick_buttons q
          WHERE q.category_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM categories c WHERE c.id = q.category_id))
    INTO orphans;

    IF orphans > 0 THEN
        RAISE EXCEPTION
            '% row(s) still point at something that is not a category. The '
            'repoint above did not cover them; investigate before re-applying.',
            orphans;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 3. Point the foreign keys at `categories`. They were dropped in step 2 so the
--    repoint could run; this puts them back, aimed at the right table.
--
--    Each keeps the ON DELETE behaviour it already had — dropping a constraint
--    drops its clauses too, so anything not restated here is silently lost.
--    `quick_buttons` is the one with a clause: SET NULL, chosen in 0010 because
--    a button whose category is gone still logs a valid uncategorised payment,
--    so it must not block the category's deletion. Payments and subscriptions
--    have none, matching payments.expense_source_id in 0001.
-- ---------------------------------------------------------------------------
ALTER TABLE payments ADD CONSTRAINT payments_category_id_fkey
    FOREIGN KEY (category_id) REFERENCES categories(id);

ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_category_id_fkey
    FOREIGN KEY (category_id) REFERENCES categories(id);

ALTER TABLE quick_buttons ADD CONSTRAINT quick_buttons_category_id_fkey
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------------
-- 4. categories_view without the compatibility layer.
--
-- The CTE that resolved a payment through `expense_sources` is gone: a payment
-- now names its category outright. Everything else is unchanged from 0025 — the
-- accrual window, the direct-spend roll-up, and the two `split` rules.
--
-- The COALESCE around `cost` and `starting_balance` goes too, dead since 0026
-- made both columns NOT NULL.
--
-- Column order is preserved exactly, so this stays a CREATE OR REPLACE and the
-- view keeps its grants.
-- ---------------------------------------------------------------------------
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
    CASE
        WHEN base.accrual = 'multi_month'
        THEN base.cost - base.current_month
        ELSE base.budget - base.current_month
    END AS remaining,
    CASE
        WHEN base.accrual = 'multi_month' THEN
            CASE
                WHEN base.cost > 0
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
