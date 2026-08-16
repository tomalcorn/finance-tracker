-- 0031_categories_view_accrued
--
-- Rename `categories_view.current_month` to `accrued`. The column has not meant
-- "this month" for every row since 0025: it is totalled over the row's own
-- accrual window, so a monthly category gets this month's payments while a pot
-- gets its starting balance plus every payment ever attributed to it. On the
-- one-offs grid it is labelled "Banked" — a name the column's own contradicted.
--
-- `accrued` rather than `banked` because one name has to serve all three grids
-- reading this view: "banked" reads well for a pot and wrongly for an expense
-- category, while "accrued over this row's window" is true of both. The
-- user-facing labels are unchanged and stay per-grid ("Spent", "Banked").
--
-- ALTER VIEW ... RENAME COLUMN rather than DROP + CREATE. A rename is the one
-- thing CREATE OR REPLACE VIEW cannot do (it requires the same column names in
-- the same order), and dropping the view would drop its privileges with it —
-- this way nothing has to be re-granted and no window exists where the view is
-- missing.
--
-- ⚠️ 0029's text is now historical: it still emits `current_month`, because
-- that is what it emitted at the time. Any future CREATE OR REPLACE of this
-- view must select the final column as `accrued`, or it will fail on the column
-- names not matching.
--
-- Idempotent: the rename is skipped when it has already happened, so a repeated
-- apply is safe like every other migration here.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'categories_view' AND column_name = 'current_month'
    ) THEN
        ALTER VIEW categories_view RENAME COLUMN current_month TO accrued;
    END IF;
END $$;
