-- 0028_categories_backfill_refresh
--
-- Re-run 0020's backfill, plus 0024's accrual pass, so anything created since
-- they were applied is picked up (#249).
--
-- `categories` has been drifting since 0020: the app still writes budget
-- trackers, expense sources and one-offs through the old tables, and nothing
-- writes categories, so any row added since is missing. This closes that gap
-- once. It has to be done again in #250, immediately before the FK is
-- retargeted, to catch whatever arrives in between — a migration runs once, so
-- that is a second file, not a re-apply of this one.
--
-- Every statement is the one from 0020/0024 verbatim. The inserts are
-- `ON CONFLICT (id) DO NOTHING`, so rows already migrated are skipped and only
-- new ones land; the accrual UPDATE is guarded on `accrual = 'monthly'`, so a
-- pot already carrying its figures is left alone. See those files for why each
-- rule is what it is — the comments here cover only what is new.
--
-- The preconditions are repeated deliberately rather than assumed to still
-- hold: a category added since 0020 could be the first to trip one, and the
-- inserts must not run over a half-valid table.

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
            '0028 will not pick one for you. Resolve them, then re-apply.',
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

-- A one-off inserted just above arrives with the 'monthly' default, which would
-- make it an ordinary category rather than a pot. 0024's pass turns it into one.
UPDATE categories c
SET accrual          = 'multi_month',
    cost             = COALESCE(oo.cost, 0),
    starting_balance = COALESCE(oo.banked, 0),
    budget           = COALESCE(oo.current_month, 0)
FROM one_offs oo
WHERE oo.id = c.id
  AND c.accrual = 'monthly';
