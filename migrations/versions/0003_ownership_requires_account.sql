-- 0003_ownership_requires_account
--
-- DB-level integrity for the ownership invariant: a joint row must carry a
-- joint_account_id. The domain already enforces this (require_joint_account_id),
-- but the database did not — this is defense in depth against a bad direct
-- write. Personal rows are unconstrained (joint_account_id stays NULL).
--
-- Applied to every owned table that T3 (#174) makes joint-aware, subscriptions
-- included.
--
-- Existing rows all default to ownership_type = 'personal', so the constraint
-- validates against current data without a NOT VALID escape hatch.
--
-- DROP ... IF EXISTS before ADD makes each statement idempotent: a repeated
-- apply drops and recreates the identical constraint rather than erroring
-- (ADD CONSTRAINT has no IF NOT EXISTS form).

ALTER TABLE payments DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE payments ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE bank_accounts DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE bank_accounts ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE expense_sources DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE expense_sources ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE income_sources DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE income_sources ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE budget_tracker DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE budget_tracker ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE one_offs DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE one_offs ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);

ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS ownership_requires_account;
ALTER TABLE subscriptions ADD CONSTRAINT ownership_requires_account
    CHECK (ownership_type = 'personal' OR joint_account_id IS NOT NULL);
