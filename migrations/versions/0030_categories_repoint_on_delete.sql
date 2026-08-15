-- 0030_categories_repoint_on_delete
--
-- Deleting a category moves everything pointing at it UP TO ITS PARENT, rather
-- than being rejected by the foreign keys 0029 aimed at `categories`.
--
-- The cutover made this urgent for pots. A one-off's payments used to hang off
-- the hidden One-offs stand-in, so deleting the pot took nothing with it and hit
-- no constraint. Now the pot holds its own payments, so `payments_category_id_fkey`
-- rejects the delete outright: a pot you have banked into cannot be deleted
-- until its payments are, and deleting the ledger history to tidy up a savings
-- goal is exactly the wrong trade.
--
-- Moving up rather than nulling, because a root is attributable now. A pot's
-- payments land on the One-offs root and a subcategory's on Expenses, so the
-- spend stays in the same place on the budget tracker — it simply stops being
-- broken out. Nothing is destroyed and no bank balance moves, since the payment
-- rows themselves are untouched.
--
-- A deleted category is always a leaf: `categories.parent_id` has no ON DELETE
-- (0020), so a category holding children cannot be deleted at all. That is why
-- one hop is enough. A *root* has nowhere to go up to, and `OLD.parent_id` is
-- then NULL — the same statement leaves its rows unattributed, which is the
-- honest answer when the thing they were attributed to is gone.
--
-- `quick_buttons` keeps the ON DELETE SET NULL it has carried since 0010, so
-- the two rules overlap on that table. The trigger wins: it runs BEFORE DELETE
-- and leaves no referencing row for the constraint to act on, which is what we
-- want — a button that moves up to the parent is a better button than the
-- uncategorised one 0010 settled for when only a stand-in was attributable. The
-- clause stays as the floor if this trigger is ever dropped.
--
-- A trigger rather than declarative FK actions: ON DELETE has no "set to the
-- deleted row's own column" mode. `categories_enforce_depth` (0020) already
-- establishes the pattern on this table. SECURITY INVOKER (the default), so the
-- UPDATEs run under the deleting user's RLS — a user can only ever repoint rows
-- they can already write.

CREATE OR REPLACE FUNCTION categories_repoint_to_parent() RETURNS TRIGGER AS $$
BEGIN
    UPDATE payments      SET category_id = OLD.parent_id WHERE category_id = OLD.id;
    UPDATE subscriptions SET category_id = OLD.parent_id WHERE category_id = OLD.id;
    UPDATE quick_buttons SET category_id = OLD.parent_id WHERE category_id = OLD.id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS categories_repoint_to_parent ON categories;
CREATE TRIGGER categories_repoint_to_parent
    BEFORE DELETE ON categories
    FOR EACH ROW EXECUTE FUNCTION categories_repoint_to_parent();
