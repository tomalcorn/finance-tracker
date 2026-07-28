-- 0013_quick_button_payment_name
--
-- A quick button names two different things, and until now they shared one
-- column: `name` labels the button on its tile, and the payment a tap logs took
-- that same label as its own name.
--
-- They are not the same thing. One "Groceries" button logs a big shop one day
-- and a pint of milk the next, so the payment's name is part of the preset the
-- button fills a payment in with — optional, and overridable at the till by a
-- prompt button's form. The tile's label stays required: a button has to say
-- what it is.
--
-- `payment_name` is therefore nullable, and NULL means "use the button's label",
-- resolved in the use case rather than backfilled here — a button whose two
-- names agree should keep tracking its label when that label is edited.
--
-- Idempotent (ADD COLUMN IF NOT EXISTS), like the other quick-button migrations.

ALTER TABLE quick_buttons ADD COLUMN IF NOT EXISTS payment_name TEXT;
