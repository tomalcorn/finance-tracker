-- 0035_contribute_to_joint_function
--
-- A one-off contribution to the joint account as one SQL function (#301), so the
-- Expo app can't leave a pair half written. It follows
-- `use_cases/contribute_to_joint.py`: a personal expense against the "Joint" root
-- category and a joint income against the chosen income source, each pointing at
-- the other. The cross-link goes through `book_joint_income_leg` from 0034.
--
-- SECURITY INVOKER, so RLS applies to every statement in prod. `p_user_id` is
-- therefore no privilege: WITH CHECK rejects a row written for anyone else. It is
-- a parameter because the test database is RLS-free and has no `user_id()`, and
-- for the same reason the rows are looked up explicitly rather than left to RLS.

CREATE OR REPLACE FUNCTION contribute_to_joint(
    p_user_id TEXT,
    p_amount DOUBLE PRECISION,
    p_from_bank_account_id UUID,
    p_to_bank_account_id UUID,
    p_income_source_id UUID,
    p_payment_date DATE
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_account UUID;
    v_account_name TEXT;
    v_category UUID;
    v_expense_id UUID := gen_random_uuid();
    v_name TEXT;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'A contribution must be more than zero.';
    END IF;

    -- At most one, enforced by one_joint_account_per_user.
    SELECT member.joint_account_id, account.name
    INTO v_account, v_account_name
    FROM joint_account_members member
    JOIN joint_accounts account ON account.id = member.joint_account_id
    WHERE member.user_id = p_user_id;

    IF v_account IS NULL THEN
        RAISE EXCEPTION 'You are not a member of a joint account to contribute to.';
    END IF;

    SELECT id INTO v_category
    FROM categories
    WHERE user_id = p_user_id
      AND ownership_type = 'personal'
      AND parent_id IS NULL
      AND name = 'Joint';

    IF v_category IS NULL THEN
        RAISE EXCEPTION 'You have no Joint budget tracker to book a contribution against.';
    END IF;

    v_name := 'Joint: ' || v_account_name;

    INSERT INTO payments (
        id, user_id, name, income, expense, payment_date, checked, bank_account_id,
        payment_type, category_id, ownership_type
    ) VALUES (
        v_expense_id, p_user_id, v_name, 0, p_amount, p_payment_date, FALSE,
        p_from_bank_account_id, 'expense', v_category, 'personal'
    );

    PERFORM book_joint_income_leg(
        p_user_id, v_account, v_expense_id, v_name, p_amount, p_payment_date,
        p_to_bank_account_id, p_income_source_id, NULL
    );
END;
$$;

-- PostgREST caches its schema, so a new function needs it reloaded to be callable.
NOTIFY pgrst, 'reload schema';
