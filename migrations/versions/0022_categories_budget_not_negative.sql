-- 0022_categories_budget_not_negative
--
-- `categories.budget` is a plan for money going out, so a negative is not a
-- smaller budget — it is nonsense. CategoryModel and CategoryView both declare
-- it `pydantic.NonNegativeFloat` (review of #253); this is the half of that rule
-- the database has to hold.
--
-- It is not belt-and-braces. A grid edit reaches the table through
-- `apply_edits`, which patches columns directly and deliberately does NOT pass
-- through the entity gate — identity and ownership columns are not editable, so
-- a patch cannot misfile a row, and that is the only invariant the gate was
-- protecting. `budget` is editable, so the entity's validator never sees it.
--
-- Without this constraint the read model is stricter than the table, which is
-- the worst of both: a negative typed into the grid persists happily, and then
-- the *next read* fails. Not for that row alone — `_validated` raises
-- RepositoryError for the whole fetch — so one bad cell takes out the page
-- behind the error boundary, with no way back to fix it from the UI.
--
-- Verified against both databases before adding: no row in categories,
-- budget_tracker, expense_sources or one_offs currently holds a negative
-- amount, so this validates against existing data without a NOT VALID escape.
--
-- Shared migration (applies to both environments): this is data integrity, not
-- RLS. 0021 is taken by the prod-only RLS overlay, which shares this sequence.
--
-- DROP ... IF EXISTS before ADD keeps it idempotent, matching 0003 and 0017.

ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_budget_is_not_negative;
ALTER TABLE categories ADD CONSTRAINT category_budget_is_not_negative
    CHECK (budget >= 0);
