-- 0006_subscriptions_view_ownership
--
-- Expose ownership_type / joint_account_id on subscriptions_view.
--
-- 0002 rewrote the other aggregate views to append these two columns but left
-- subscriptions_view on its original `SELECT s.*` form, assuming the star would
-- pick up the new table columns. It does not: a view's `*` is expanded to the
-- columns present when the view was created and then frozen, so adding
-- ownership_type / joint_account_id to the subscriptions *table* in 0002 never
-- reached the view. That was harmless until the ownership-aware cache split
-- (#176) began filtering subscription reads on ownership_type, which failed with
-- 'column subscriptions_view.ownership_type does not exist'.
--
-- CREATE OR REPLACE requires the existing columns to keep their name, type and
-- order and only allows appending, so the original columns and monthly_cost are
-- listed explicitly (matching the frozen `s.*` expansion) with the two ownership
-- columns appended at the end — exactly the shape 0002 gave the other views.
-- Replacing in place (rather than DROP + CREATE) preserves the view's grants.

CREATE OR REPLACE VIEW subscriptions_view WITH (security_invoker = on) AS
SELECT
    s.id,
    s.user_id,
    s.name,
    s.amount,
    s.cadence,
    s.bank_account_id,
    s.expense_source_id,
    s.start_date,
    s.end_date,
    s.is_active,
    s._created_at,
    CASE s.cadence
        WHEN 'weekly' THEN s.amount * 52.0 / 12.0
        WHEN 'biannually' THEN s.amount / 6.0
        WHEN 'monthly' THEN s.amount
        WHEN 'quarterly' THEN s.amount / 3.0
        WHEN 'yearly' THEN s.amount / 12.0
        ELSE 0
    END AS monthly_cost,
    s.ownership_type,
    s.joint_account_id
FROM subscriptions s;
