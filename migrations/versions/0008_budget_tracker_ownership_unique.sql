-- 0008_budget_tracker_ownership_unique
--
-- The original UNIQUE (user_id, name) on budget_tracker (0001) predates the
-- ownership dimension. It forbids one user from having both a personal and a
-- joint budget tracker of the same name ("Expenses", "One-Offs", "Savings"), so
-- seeding a joint workspace for a user who already has a personal one fails with
-- a 23505 duplicate-key error. Replace it with ownership-aware uniqueness.
--
--   * Personal trackers: unique per (user_id, name) — unchanged in spirit, just
--     scoped to the personal rows.
--   * Joint trackers: unique per (joint_account_id, name). A joint tracker is
--     shared across the account's members, so uniqueness is per account, not per
--     member — two members must not each seed their own "Expenses".
--
-- Partial unique indexes (not table constraints) because the scope differs by
-- ownership_type. Both drop-then-create for idempotency, matching the other
-- constraint migrations. The old constraint is dropped under both the name a
-- from-scratch 0001 apply generates (budget_tracker_user_id_name_key) and the
-- name carried on the baselined live databases (budget_tracker_user_name_unique).

ALTER TABLE budget_tracker DROP CONSTRAINT IF EXISTS budget_tracker_user_id_name_key;
ALTER TABLE budget_tracker DROP CONSTRAINT IF EXISTS budget_tracker_user_name_unique;

DROP INDEX IF EXISTS budget_tracker_personal_user_name_unique;
CREATE UNIQUE INDEX budget_tracker_personal_user_name_unique
    ON budget_tracker (user_id, name)
    WHERE ownership_type = 'personal';

DROP INDEX IF EXISTS budget_tracker_joint_account_name_unique;
CREATE UNIQUE INDEX budget_tracker_joint_account_name_unique
    ON budget_tracker (joint_account_id, name)
    WHERE ownership_type = 'joint';
