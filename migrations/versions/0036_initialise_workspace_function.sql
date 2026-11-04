-- 0036_initialise_workspace_function
--
-- First-run workspace setup as one SQL function (#302), following
-- `use_cases/initialise_workspace.py` and `use_cases/initialise_joint_workspace.py`.
-- A half gets its budget trackers, which are root categories, and its settings row
-- at the default. A joint account gets every tracker but "Joint": that one is the
-- personal-side anchor for contributions, meaningless inside the account itself.
--
-- One call per half, so a failure on the joint side can't stop the personal one.
-- A user in no joint account has nothing to seed, so a joint call does nothing for
-- them rather than raising.
--
-- It differs from the Python versions in one deliberate way: they read what exists
-- and then write what is missing, so two tabs or two members of a joint account
-- can race into a unique-index error. Here the partial unique indexes from 0015
-- and 0020 decide. ON CONFLICT DO NOTHING has no conflict target, so it covers all
-- of them, and a row that already exists is left as it is.
--
-- SECURITY INVOKER, so RLS applies to every statement in prod. `p_user_id` is
-- therefore no privilege: WITH CHECK rejects a row written for anyone else. It is
-- a parameter because the test database is RLS-free and has no `user_id()`.

CREATE OR REPLACE FUNCTION initialise_workspace(
    p_user_id TEXT,
    p_ownership TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_account UUID;
BEGIN
    IF p_ownership = 'personal' THEN
        INSERT INTO categories (id, user_id, name, ownership_type)
        SELECT gen_random_uuid(), p_user_id, tracker, 'personal'
        FROM unnest(ARRAY['Expenses', 'Joint', 'One-offs', 'Savings']) AS tracker
        ON CONFLICT DO NOTHING;

        INSERT INTO user_settings (id, user_id, ownership_type)
        VALUES (gen_random_uuid(), p_user_id, 'personal')
        ON CONFLICT DO NOTHING;
    ELSIF p_ownership = 'joint' THEN
        -- At most one, enforced by one_joint_account_per_user.
        SELECT joint_account_id INTO v_account
        FROM joint_account_members
        WHERE user_id = p_user_id;

        IF v_account IS NULL THEN
            RETURN;
        END IF;

        INSERT INTO categories (id, user_id, name, ownership_type, joint_account_id)
        SELECT gen_random_uuid(), p_user_id, tracker, 'joint', v_account
        FROM unnest(ARRAY['Expenses', 'One-offs', 'Savings']) AS tracker
        ON CONFLICT DO NOTHING;

        INSERT INTO user_settings (id, user_id, ownership_type, joint_account_id)
        VALUES (gen_random_uuid(), p_user_id, 'joint', v_account)
        ON CONFLICT DO NOTHING;
    ELSE
        RAISE EXCEPTION 'Unknown ownership: %', p_ownership;
    END IF;
END;
$$;

-- PostgREST caches its schema, so a new function needs it reloaded to be callable.
NOTIFY pgrst, 'reload schema';
