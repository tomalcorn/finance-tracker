-- 0012_quick_button_modes
--
-- A quick button now does one of two things when tapped (#60): log its preset
-- straight away, or open a payment form pre-filled with whatever it holds so the
-- varying part — usually the amount — can be typed in first.
--
-- A prompt button exists precisely to leave fields blank, so `expense` and
-- `bank_account_id` become nullable. The CHECK keeps the guarantee that matters:
-- a button that logs on tap must still hold everything a payment needs, so it
-- cannot be tapped into a half-written row. That mirrors the domain's own
-- `_check_loggable` validator, the same defense-in-depth as
-- `ownership_requires_account` (0003).
--
-- A follow-up rather than an edit to 0010: that migration is already applied to
-- the test database, and the runner records it as applied, so an in-place change
-- would silently never run there.
--
-- Statements are idempotent (ADD COLUMN IF NOT EXISTS / DROP NOT NULL is a
-- no-op when already dropped / DROP CONSTRAINT IF EXISTS before ADD).

ALTER TABLE quick_buttons ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'log';

ALTER TABLE quick_buttons ALTER COLUMN expense DROP NOT NULL;
ALTER TABLE quick_buttons ALTER COLUMN bank_account_id DROP NOT NULL;

ALTER TABLE quick_buttons DROP CONSTRAINT IF EXISTS quick_button_mode_is_known;
ALTER TABLE quick_buttons ADD CONSTRAINT quick_button_mode_is_known
    CHECK (mode IN ('log', 'prompt'));

ALTER TABLE quick_buttons DROP CONSTRAINT IF EXISTS log_button_is_loggable;
ALTER TABLE quick_buttons ADD CONSTRAINT log_button_is_loggable
    CHECK (
        mode <> 'log'
        OR (expense IS NOT NULL AND expense > 0 AND bank_account_id IS NOT NULL)
    );
