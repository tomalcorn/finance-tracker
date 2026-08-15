-- 0026_categories_pot_fields_not_null
--
-- Make `cost` and `starting_balance` mandatory, defaulting to 0 (review of
-- #256). 0024 made them nullable and tied their presence to `accrual`; carrying
-- 0 on a monthly category is simpler than policing when they may be set, and
-- takes a constraint and two entity errors out of the model with it.
--
-- Follows 0024 rather than revising it: 0024 is applied to prod, so its content
-- is now history.
--
-- The old constraint has to go first — it requires both columns to be NULL for a
-- monthly category, which is exactly what the backfill below stops being true.

ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_accrual_columns_match;

UPDATE categories SET cost = 0 WHERE cost IS NULL;
UPDATE categories SET starting_balance = 0 WHERE starting_balance IS NULL;

ALTER TABLE categories ALTER COLUMN cost SET DEFAULT 0;
ALTER TABLE categories ALTER COLUMN cost SET NOT NULL;

ALTER TABLE categories ALTER COLUMN starting_balance SET DEFAULT 0;
ALTER TABLE categories ALTER COLUMN starting_balance SET NOT NULL;

-- category_cost_is_not_negative (0024) still applies and needs no change: its
-- `cost IS NULL OR` branch simply stops being reachable.
--
-- starting_balance keeps no sign constraint, as bank_accounts.starting_balance
-- does not: an account can start overdrawn, and the same licence lets money be
-- moved out of a pot that was filled by payments.
