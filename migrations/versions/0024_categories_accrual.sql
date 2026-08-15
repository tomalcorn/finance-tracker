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
--   * **A pot's balance is its starting balance plus the payments attributed to
--     it**, accumulated across months. Bank It! stops moving a private counter
--     and simply writes a payment against the pot.
--
-- So `accrual` is not a second way of computing things — it only picks the
-- window, and 0025 branches the view on it.
--
-- `starting_balance` is modelled directly on `bank_accounts.starting_balance`,
-- and behaves the same way: a figure you set, which nothing writes afterwards,
-- with payments accumulating on top —
--
--     ba.starting_balance + COALESCE(SUM(p.income - p.expense), 0)
--
-- That is deliberately NOT a stored running total. A counter that payments also
-- updated would be a second source of truth for the same money and would need
-- unwinding whenever a payment was edited or deleted. A starting balance cannot
-- drift, because it describes where the pot began, not where it is now.
--
-- It carries the balances that predate pots being able to take payments:
-- `one_offs.banked` holds £2,185.50 with only £235.50 of matching `Bank:`
-- payment rows, so the rest has no ledger history to rebuild from. Inventing
-- payments for it was rejected — bank_accounts_view sums payments, so that
-- would take £1,950 off the account balances for money that never left them.
-- As a starting balance it simply carries over, whole.
--
-- Like its bank-account counterpart it takes NO non-negative constraint. An
-- overdrawn account starts below zero, and by the same licence a pot's starting
-- balance can go negative — which is what lets money be moved out of a pot that
-- was filled by payments.
--
-- Statements are idempotent (ADD COLUMN IF NOT EXISTS, DROP CONSTRAINT IF
-- EXISTS before ADD, a backfill guarded on the column still being unset).

ALTER TABLE categories ADD COLUMN IF NOT EXISTS accrual TEXT NOT NULL DEFAULT 'monthly';
ALTER TABLE categories ADD COLUMN IF NOT EXISTS cost FLOAT;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS starting_balance FLOAT;

ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_accrual_is_known;
ALTER TABLE categories ADD CONSTRAINT category_accrual_is_known
    CHECK (accrual IN ('monthly', 'multi_month'));

-- The pot columns belong to multi-month pots and to nothing else: both set for
-- one, neither set for anything else. A pot needs a target to be measured
-- against and a balance to start from; a monthly category resets, so it has
-- nothing to do with either. Same shape as 0017's
-- joint_contribution_is_complete.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_accrual_columns_match;
ALTER TABLE categories ADD CONSTRAINT category_accrual_columns_match
    CHECK (
        (accrual = 'multi_month')
        = (cost IS NOT NULL AND starting_balance IS NOT NULL)
    );

-- A root is always monthly. This is the correction to #248's own plan, which
-- had accrual inherited from the root: root and children genuinely differ. The
-- One-offs ROOT is a monthly allowance — "£599.68 a month towards one-offs, of
-- which £240.83 used" — while each pot under it accumulates until it is full.
-- Inheriting would have made the root read as an all-time total.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_multi_month_is_a_child;
ALTER TABLE categories ADD CONSTRAINT category_multi_month_is_a_child
    CHECK (accrual = 'monthly' OR parent_id IS NOT NULL);

-- Like budget in 0022: a pot costing a negative amount is nonsense.
ALTER TABLE categories DROP CONSTRAINT IF EXISTS category_cost_is_not_negative;
ALTER TABLE categories ADD CONSTRAINT category_cost_is_not_negative
    CHECK (cost IS NULL OR cost >= 0);

-- Backfill the amounts 0020 deliberately left behind, from the one_offs rows
-- they came from. Ids were preserved, so the join is on id alone.
--
-- one_offs.current_month is "Planned Spend" — what you intend to put in this
-- month — which is exactly what `budget` means for every other category, so it
-- lands there. That also keeps `split` faithful: one_offs_view divided the
-- pledge by the tracker's budget, and categories_view divides `budget` by the
-- parent's.
--
-- `one_offs.banked` becomes the pot's starting balance, which carries every
-- penny of it across without touching a single account balance.
--
-- The four existing `Bank:` payments (£235.50) are part of that figure, so they
-- must NOT also be repointed onto their pots in #249 — that would count them
-- twice. They stay resolved to the One-offs root, like every other payment
-- against the hidden stand-in.
--
-- `one_offs` is left fully intact regardless, so the original figures remain
-- recoverable until the old tables are dropped.
--
-- Guarded on accrual still being 'monthly' so a re-apply cannot overwrite a
-- pot that has since been edited.
UPDATE categories c
SET accrual          = 'multi_month',
    cost             = COALESCE(oo.cost, 0),
    starting_balance = COALESCE(oo.banked, 0),
    budget           = COALESCE(oo.current_month, 0)
FROM one_offs oo
WHERE oo.id = c.id
  AND c.accrual = 'monthly';
