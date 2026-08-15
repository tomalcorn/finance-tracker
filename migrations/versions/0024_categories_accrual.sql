-- 0024_categories_accrual
--
-- The accrual dimension (#248, epic #239): whether a category's spend totals
-- over the current calendar month or over all time.
--
-- Settled in #239: one-offs stay multi-month. An expense category resets every
-- month; a one-off pot accumulates until it is full. With both in `categories`,
-- that becomes a property of the row — and, in the end, ONLY a payment window.
--
-- What a one-off pot means (settled while building this):
--
--   * **Planned Spend** is a plan for the month, set at the start of it. Nothing
--     decrements it — not Bank It!, not payments. It is the pot's monthly
--     allowance, so it merges into `budget` like every other category's.
--   * **Money in the pot is payments attributed to it**, accumulated across
--     months. Bank It! stops moving a private counter and simply writes a
--     payment against the pot.
--
-- So `accrual` is not a second way of computing things — it only picks the
-- window, and 0025 branches the view on it.
--
-- `banked` survives for one reason: it is an OPENING BALANCE. £2,185.50 of it
-- accrued before pots could take payments, and only £235.50 of that exists as
-- `Bank:` payments, so the rest has no ledger history to recover it from.
-- Inventing payments to represent it was rejected outright — bank_accounts_view
-- sums payments, so that would corrupt every account balance. It is therefore
-- money brought forward, and the view adds attributed payments on top of it.
--
-- Statements are idempotent (ADD COLUMN IF NOT EXISTS, DROP CONSTRAINT IF
-- EXISTS before ADD, a backfill guarded on the column still being unset).

ALTER TABLE categories ADD COLUMN IF NOT EXISTS accrual TEXT NOT NULL DEFAULT 'monthly';
ALTER TABLE categories ADD COLUMN IF NOT EXISTS cost FLOAT;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS banked FLOAT;

ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_accrual_is_known;
ALTER TABLE categories ADD CONSTRAINT category_accrual_is_known
    CHECK (accrual IN ('monthly', 'multi_month'));

-- The accrual columns belong to multi-month pots and to nothing else: both set
-- for one, neither set for anything else. Same shape as 0017's
-- joint_contribution_is_complete.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_accrual_columns_match;
ALTER TABLE categories ADD CONSTRAINT category_accrual_columns_match
    CHECK ((accrual = 'multi_month') = (cost IS NOT NULL AND banked IS NOT NULL));

-- A root is always monthly. This is the correction to #248's own plan, which
-- had accrual inherited from the root: root and children genuinely differ. The
-- One-offs ROOT is a monthly allowance — "£599.68 a month towards one-offs, of
-- which £240.83 used" — while each pot under it accumulates until it is full.
-- Inheriting would have made the root read as an all-time total.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_multi_month_is_a_child;
ALTER TABLE categories ADD CONSTRAINT category_multi_month_is_a_child
    CHECK (accrual = 'monthly' OR parent_id IS NOT NULL);

-- Amounts, like budget in 0022. A pot costing a negative amount is nonsense,
-- and a negative opening balance is money that was never put in.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_cost_is_not_negative;
ALTER TABLE categories ADD CONSTRAINT category_cost_is_not_negative
    CHECK (cost IS NULL OR cost >= 0);

ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_banked_is_not_negative;
ALTER TABLE categories ADD CONSTRAINT category_banked_is_not_negative
    CHECK (banked IS NULL OR banked >= 0);

-- Backfill the amounts 0020 deliberately left behind, from the one_offs rows
-- they came from. Ids were preserved, so the join is on id alone.
--
-- one_offs.current_month is "Planned Spend" — what you intend to put in this
-- month — which is exactly what `budget` means for every other category, so it
-- lands there. That also keeps `split` faithful: one_offs_view divided the
-- pledge by the tracker's budget, and categories_view divides `budget` by the
-- parent's.
--
-- Guarded on accrual still being 'monthly' so a re-apply cannot overwrite a
-- pot that has since been edited.
UPDATE categories c
SET accrual = 'multi_month',
    cost    = COALESCE(oo.cost, 0),
    banked  = COALESCE(oo.banked, 0),
    budget  = COALESCE(oo.current_month, 0)
FROM one_offs oo
WHERE oo.id = c.id
  AND c.accrual = 'monthly';
