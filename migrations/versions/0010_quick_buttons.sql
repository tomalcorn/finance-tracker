-- 0010_quick_buttons
--
-- The quick-entry buttons behind the Quick Expenses page (#60): one row per
-- preset expense a user can log with a single tap.
--
-- The table carries the ownership dimension from the start, so a button belongs
-- either to one user personally or to a joint account the way every other owned
-- aggregate does. A joint button is shared: either member sees it and tapping it
-- books the payment into the joint ledger.
--
-- No view: the row has no computed columns, so reads hit the table directly
-- (like payments and the joint tables).
--
-- bank_account_id / expense_source_id are the payment fields a tap fills in, so
-- they reference the same tables payments does. ON DELETE CASCADE on the bank
-- account and SET NULL on the expense source mirror what each means for a
-- button: a button whose account is gone can no longer be logged at all, while
-- one whose expense source is gone still logs a valid uncategorised payment.
--
-- Statements are idempotent (IF NOT EXISTS / DROP ... IF EXISTS before ADD) so a
-- partial or repeated apply is safe, matching the other migrations.

CREATE TABLE IF NOT EXISTS quick_buttons (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    expense FLOAT NOT NULL DEFAULT 0,
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    expense_source_id UUID REFERENCES expense_sources(id) ON DELETE SET NULL,
    icon TEXT,
    display_order INT NOT NULL DEFAULT 0,
    ownership_type TEXT NOT NULL DEFAULT 'personal',
    joint_account_id UUID REFERENCES joint_accounts(id),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Same ownership invariant as every other owned table (0003): a joint row must
-- name the account it belongs to.
ALTER TABLE quick_buttons DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE quick_buttons ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);
