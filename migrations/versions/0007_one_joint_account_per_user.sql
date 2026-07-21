-- 0007_one_joint_account_per_user
--
-- A user belongs to at most one joint account. That is a deliberate product
-- decision, and the repositories now rely on it: an ownership-scoped repository
-- resolves the user's *single* joint account id to build the shared
-- `joint:{account_id}:{table}` cache key. Make the invariant real in the schema
-- rather than assumed in code, so a second membership row fails loudly here
-- instead of silently making one of the two accounts invisible.
--
-- The existing UNIQUE (joint_account_id, user_id) still prevents duplicate
-- membership of the *same* account; this adds the stricter "one account, full
-- stop" rule on user_id alone.
--
-- DROP ... IF EXISTS before ADD keeps the statement idempotent, matching the
-- other constraint migrations.

ALTER TABLE joint_account_members
    DROP CONSTRAINT IF EXISTS one_joint_account_per_user;
ALTER TABLE joint_account_members
    ADD CONSTRAINT one_joint_account_per_user UNIQUE (user_id);
