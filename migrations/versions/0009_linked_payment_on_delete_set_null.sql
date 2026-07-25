-- 0009_linked_payment_on_delete_set_null
--
-- `payments.linked_payment_id` (0002) was created with no ON DELETE clause, so
-- it defaults to NO ACTION. A contribution cross-links its two legs — the
-- personal expense points at the joint income and the income points back — so
-- *either* row is referenced by the other and neither can be deleted:
--
--   ERROR: update or delete on table "payments" violates foreign key constraint
--          "payments_linked_payment_id_fkey" on table "payments"
--
-- Recreate the constraint with ON DELETE SET NULL: deleting one leg clears the
-- surviving row's back-reference instead of blocking the delete. The surviving
-- leg is deliberately left in place — SET NULL rather than CASCADE — so that
-- deleting a personal row can never silently remove a row from the shared joint
-- ledger the other member sees. Removing both legs stays an explicit act on
-- each side.
--
-- DROP ... IF EXISTS before ADD keeps the statement idempotent, matching the
-- other constraint migrations. The constraint is dropped under the name
-- Postgres generates for it (payments_linked_payment_id_fkey).

ALTER TABLE payments
    DROP CONSTRAINT IF EXISTS payments_linked_payment_id_fkey;
ALTER TABLE payments
    ADD CONSTRAINT payments_linked_payment_id_fkey
    FOREIGN KEY (linked_payment_id) REFERENCES payments(id) ON DELETE SET NULL;
