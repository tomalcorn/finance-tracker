-- 0020_categories
--
-- One self-referential `categories` table replacing budget_tracker,
-- expense_sources and one_offs (#246, epic #239). A budget tracker and an
-- expense source were always the same thing at two levels — the two views
-- compute identical figures from different inputs — so they become one table
-- with a `parent_id`, and a payment points at a category at any level.
--
-- ADDITIVE ONLY. The three old tables and their views are left untouched and
-- keep serving the app, so this migration is safe to apply on its own. The
-- cutover happens across #247 (categories_view), #249 (payments.category_id),
-- #250-#252 (UI), and a later migration drops the old tables. Until then the
-- copy made here goes stale — nothing writes to `categories` yet.
--
-- IDS ARE PRESERVED. Each row keeps the id it had in its source table, which is
-- what makes #249 cheap: payments.expense_source_id and one_offs' own ids
-- already hold values that are valid `categories` ids, so the FK repoint is a
-- rename rather than a remapping. Collisions are impossible — every id is a v4
-- UUID from a distinct table.
--
-- The accrual dimension (`cost`, `banked`, monthly vs multi-month) is
-- deliberately NOT here: it is #248, so this migration stays about the shape.
-- One-offs' `cost`/`current_month`/`banked` are therefore *not* copied yet, and
-- #248 backfills them from `one_offs` while that table is still present.
--
-- Statements are idempotent (CREATE TABLE IF NOT EXISTS, DROP ... IF EXISTS
-- before ADD/CREATE, ON CONFLICT DO NOTHING on the backfill).

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    -- No ON DELETE action, matching payments.expense_source_id (0001): deleting
    -- a category that still holds children fails loudly rather than silently
    -- taking the children with it. Roots are seeded and not deletable anyway.
    parent_id UUID REFERENCES categories(id),
    budget FLOAT NOT NULL DEFAULT 0,
    ownership_type TEXT NOT NULL DEFAULT 'personal',
    joint_account_id UUID REFERENCES joint_accounts(id),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- The ownership invariant, as on every other owned table (0003).
ALTER TABLE categories DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE categories ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

-- A category may not be its own parent. Deeper cycles are impossible once the
-- depth rule below holds, but a self-reference slips past it (a row pointing at
-- itself never reads as "my parent has a parent" until it already exists).
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_is_not_its_own_parent;
ALTER TABLE categories ADD CONSTRAINT category_is_not_its_own_parent
    CHECK (parent_id IS NULL OR parent_id <> id);

-- Ownership-aware uniqueness, following 0008's shape and adding the parent
-- scope: two roots of a user cannot share a name, and neither can two children
-- of the same parent — but "Travel" may exist under both Expenses and One-offs.
-- Partial indexes rather than table constraints because the scope differs by
-- ownership_type, and because NULL never compares equal, so a single
-- UNIQUE (user_id, parent_id, name) would not constrain roots at all.
DROP INDEX IF EXISTS categories_personal_root_name_unique;
CREATE UNIQUE INDEX categories_personal_root_name_unique
    ON categories (user_id, name)
    WHERE ownership_type = 'personal' AND parent_id IS NULL;

DROP INDEX IF EXISTS categories_personal_child_name_unique;
CREATE UNIQUE INDEX categories_personal_child_name_unique
    ON categories (user_id, parent_id, name)
    WHERE ownership_type = 'personal' AND parent_id IS NOT NULL;

DROP INDEX IF EXISTS categories_joint_root_name_unique;
CREATE UNIQUE INDEX categories_joint_root_name_unique
    ON categories (joint_account_id, name)
    WHERE ownership_type = 'joint' AND parent_id IS NULL;

DROP INDEX IF EXISTS categories_joint_child_name_unique;
CREATE UNIQUE INDEX categories_joint_child_name_unique
    ON categories (joint_account_id, parent_id, name)
    WHERE ownership_type = 'joint' AND parent_id IS NOT NULL;

-- The tree is exactly two levels deep: a root, and its children. #247 relies on
-- it — with depth bounded, categories_view is a self-join instead of a
-- WITH RECURSIVE, which is materially easier to reason about.
--
-- A CHECK cannot express this (it cannot see other rows), so it is a trigger.
-- Both directions have to be guarded: attaching a child to a child, and giving
-- a parent to a row that already has children. The declarative alternative — a
-- generated `is_root` column plus a composite self-FK — enforces both at once
-- but costs two columns and a redundant unique index to point at, and reads as
-- a puzzle; this is longer but says what it means.
CREATE OR REPLACE FUNCTION categories_enforce_depth() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM categories
            WHERE id = NEW.parent_id AND parent_id IS NOT NULL
        ) THEN
            RAISE EXCEPTION
                'category "%" cannot hang off a subcategory: categories are two levels deep',
                NEW.name;
        END IF;

        IF EXISTS (SELECT 1 FROM categories WHERE parent_id = NEW.id) THEN
            RAISE EXCEPTION
                'category "%" has subcategories of its own, so it cannot be given a parent',
                NEW.name;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS categories_enforce_depth ON categories;
CREATE TRIGGER categories_enforce_depth
    BEFORE INSERT OR UPDATE OF parent_id ON categories
    FOR EACH ROW EXECUTE FUNCTION categories_enforce_depth();

-- Backfill preconditions.
--
-- The backfill makes three assumptions about the old data. Each is true of data
-- the app itself wrote, and each would otherwise fail silently or cryptically,
-- so all three are checked up front with a message a human can act on. Every
-- one of them is a decision for a person, not something a migration should
-- guess at.
DO $$
DECLARE
    offenders INT;
BEGIN
    -- 1. An expense source's tracker link is a single-element array in
    -- practice: budget_tracker_ids is visible=False in the grid config, never
    -- editable, and set once from extra_row_values. Two links means the [1]
    -- subscript below would silently drop one.
    SELECT COUNT(*) INTO offenders
    FROM expense_sources
    WHERE COALESCE(array_length(budget_tracker_ids, 1), 0) > 1;
    IF offenders > 0 THEN
        RAISE EXCEPTION
            '% expense_sources row(s) link to more than one budget tracker; '
            '0020 will not pick one for you. Resolve them, then re-apply.',
            offenders;
    END IF;

    -- 2. Every row being migrated has a parent to hang off. An expense source
    -- with no tracker link is already invisible in the UI (the Expenses tab
    -- filters on array_contains), but dropping it here would be silent data
    -- loss, and there is no sensible parent to invent for it.
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

    -- 3. Names are present. categories.name is NOT NULL (as budget_tracker.name
    -- always was), while expense_sources.name and one_offs.name are nullable
    -- from 0001 — the grid's required=True came later and guards only the
    -- widget. A blank name would also make the uniqueness indexes above
    -- meaningless for the rows carrying it.
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

-- Roots, from budget_tracker. total_budget and budget are the same number at
-- two levels, so they merge into one column.
INSERT INTO categories (
    id, user_id, name, parent_id, budget,
    ownership_type, joint_account_id, _created_at
)
SELECT
    bt.id, bt.user_id, bt.name, NULL, bt.total_budget,
    bt.ownership_type, bt.joint_account_id, bt._created_at
FROM budget_tracker bt
ON CONFLICT (id) DO NOTHING;

-- Children, from expense_sources — except the three hidden ones.
--
-- A hidden source exists only to stand in for its tracker, because a payment
-- cannot point at a tracker today (_ensure_hidden_expense_sources). Roots are
-- directly attributable now, so those rows have no counterpart here and are
-- dropped rather than migrated. #249 repoints their payments onto the matching
-- root when it moves the FK; it identifies them the same way this does, and
-- expense_sources is still present at that point.
--
-- "Hidden" is both conditions together — named after a root AND linked to the
-- tracker of that name — so a genuine user category that happens to be called
-- "Savings" under Expenses is migrated normally.
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

-- Children, from one_offs. `cost`/`current_month`/`banked` are left behind for
-- #248 to bring over with the accrual dimension they belong to; `budget` starts
-- at its default, so a one-off category reads as an unbudgeted pot until then.
INSERT INTO categories (
    id, user_id, name, parent_id, budget,
    ownership_type, joint_account_id, _created_at
)
SELECT
    oo.id, oo.user_id, oo.name, oo.budget_tracker_id, 0,
    oo.ownership_type, oo.joint_account_id, oo._created_at
FROM one_offs oo
ON CONFLICT (id) DO NOTHING;
