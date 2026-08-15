-- 0027_rename_expense_source_id_to_category_id
--
-- Rename the attribution column on every table that carries it (#249, epic
-- #239). Money does not come *from* an expense source; it is a plan for money
-- going out, which is what every budgeting app calls a category.
--
-- A pure rename. No row moves, no view is redefined, and nothing changes about
-- what any figure means.
--
-- The FOREIGN KEY still points at `expense_sources`, deliberately. Retargeting
-- it at `categories` cannot happen yet: 17 payments and 3 subscriptions point at
-- hidden stand-in sources that have no `categories` row, so the constraint would
-- be rejected outright. Repointing them first would move them somewhere
-- `expense_sources_view` cannot see, blanking Joint / Savings / One-offs on the
-- live budget tracker page until the UI cutover several tickets later. The
-- repoint, the retarget and the deletion of `categories_view`'s temporary CTE
-- therefore all move together in #250.
--
-- The interim state is less odd than it looks: ids were preserved in 0020, so an
-- ordinary expense source's id already IS its category's id. Only the stand-ins
-- differ, and they are exactly what #250 resolves.
--
-- Dependent views need no attention. Postgres stores a view as a parse tree
-- referencing column numbers, not names, so `expense_sources_view` and
-- `categories_view` keep computing identical totals across the rename —
-- verified against prod in a rolled-back transaction.
--
-- A view's OWN output column is a different matter, and is the trap here: it
-- does not follow the base table. `subscriptions_view.expense_source_id` still
-- reads under the old name after the table is renamed, and `SubscriptionView`
-- would fail to validate. `CREATE OR REPLACE VIEW` cannot fix it — it refuses to
-- rename a column — so it takes an explicit `ALTER VIEW ... RENAME COLUMN`.

ALTER TABLE payments       RENAME COLUMN expense_source_id TO category_id;
ALTER TABLE subscriptions  RENAME COLUMN expense_source_id TO category_id;
ALTER TABLE quick_buttons  RENAME COLUMN expense_source_id TO category_id;

-- Constraint names do not follow their column, so they would otherwise keep
-- advertising the old one for as long as the constraint lives.
ALTER TABLE payments
    RENAME CONSTRAINT payments_expense_source_id_fkey TO payments_category_id_fkey;
ALTER TABLE subscriptions
    RENAME CONSTRAINT subscriptions_expense_source_id_fkey
    TO subscriptions_category_id_fkey;
ALTER TABLE quick_buttons
    RENAME CONSTRAINT quick_buttons_expense_source_id_fkey
    TO quick_buttons_category_id_fkey;

ALTER VIEW subscriptions_view RENAME COLUMN expense_source_id TO category_id;
