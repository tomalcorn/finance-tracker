-- 0018_quick_button_negative_amounts
--
-- A quick button may now preset a negative amount (#230). A negative expense
-- against the original expense source is one of the two supported ways to record
-- being paid back, so a standing "shared dinner, half back" button is an ordinary
-- thing to want — and the reason quick buttons exist is exactly this kind of
-- small repeated entry.
--
-- `log_button_is_loggable` (0012) required `expense > 0`, which ruled that out
-- for a button that logs on tap. The guarantee worth keeping is narrower: a tap
-- must move *some* money, so zero is refused and anything else is allowed. This
-- mirrors the domain's `_check_amount_moves_money` validator, the same
-- defense-in-depth as `ownership_requires_account` (0003).
--
-- No data migration is needed: every existing row satisfies `expense <> 0`,
-- because the constraint it replaces was strictly stronger.
--
-- A follow-up rather than an edit to 0012: that migration is already applied to
-- both databases and the runner records it as applied, so an in-place change
-- would silently never run.
--
-- Statements are idempotent (DROP CONSTRAINT IF EXISTS before ADD).

ALTER TABLE quick_buttons DROP CONSTRAINT IF EXISTS log_button_is_loggable;
ALTER TABLE quick_buttons ADD CONSTRAINT log_button_is_loggable
    CHECK (
        mode <> 'log'
        OR (expense IS NOT NULL AND expense <> 0 AND bank_account_id IS NOT NULL)
    );

-- A prompt button's preset is optional, so it may be NULL — but if it is set, it
-- has to move money too. 0012 left this unconstrained because the field
-- constraint on the entity covered it; that constraint is now "not zero" rather
-- than "positive", so the table states it directly.
ALTER TABLE quick_buttons DROP CONSTRAINT IF EXISTS quick_button_amount_moves_money;
ALTER TABLE quick_buttons ADD CONSTRAINT quick_button_amount_moves_money
    CHECK (expense IS NULL OR expense <> 0);
