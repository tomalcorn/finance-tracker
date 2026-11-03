-- 0034_reconcile_subscriptions_function
--
-- Subscription reconciliation as one SQL function (#298), so the Streamlit and
-- Expo apps share a single implementation rather than a Python one and a
-- TypeScript port. It replaces `use_cases/reconcile_subscriptions.py`, rule for
-- rule, for each subscription:
--
--   * inactive or expired: delete its future payments;
--   * ends before a future payment: delete that payment;
--   * otherwise, with no future payment left: book the next one due, moving on a
--     cycle if a payment already in the books settles the scheduled one.
--
-- Past payments are never touched. "Future" includes today.
--
-- A joint contribution books a cross-linked pair instead of a lone expense:
-- a personal expense and a joint income, each pointing at the other. Its repair
-- pass finishes any surviving future expense whose income is missing, or that is
-- only missing its forward link. Every write here is in one transaction, so this
-- function cannot leave a pair half written itself; the repair is for pairs the
-- Python version left behind.
--
-- It differs from the Python version in two deliberate ways:
--
--   * A user with no joint account is not an error. Their leftover contributions
--     are left alone and everything else is reconciled, where Python raised and
--     stopped the page.
--   * Runs are serialised per ledger by an advisory lock, so two tabs or two
--     members of a joint account can't each see "nothing booked" and both book.
--
-- SECURITY INVOKER, so RLS applies to every statement in prod. `p_user_id` is
-- therefore no privilege: WITH CHECK rejects a row written for anyone else. It is
-- a parameter because the test database is RLS-free and has no `user_id()`, and
-- for the same reason the rows are filtered explicitly rather than left to RLS.
--
-- `p_today` defaults to the database's date, which is UTC on Supabase, as the
-- Python version's was. It is a parameter so tests can fix it.

CREATE OR REPLACE FUNCTION subscription_cadence_step(p_cadence TEXT)
RETURNS INTERVAL
LANGUAGE plpgsql
IMMUTABLE
SET search_path = public
AS $$
BEGIN
    CASE lower(p_cadence)
        WHEN 'weekly' THEN RETURN INTERVAL '1 week';
        WHEN 'monthly' THEN RETURN INTERVAL '1 month';
        WHEN 'quarterly' THEN RETURN INTERVAL '3 months';
        WHEN 'biannually' THEN RETURN INTERVAL '6 months';
        WHEN 'yearly' THEN RETURN INTERVAL '1 year';
        ELSE RAISE EXCEPTION 'Unknown cadence: %', p_cadence;
    END CASE;
END;
$$;

-- The date a subscription's next payment falls due, or NULL if it ends first.
--
-- The scheduled date falling on or after today is the candidate. A cycle claims
-- every payment nearer to its own date than to the previous cycle's, so a charge
-- re-dated to when the money actually moved still settles that cycle, and the
-- candidate moves on to the following one.
--
-- Steps are taken one at a time from the start date, so a 31st drifts to the 28th
-- after February and stays there, as it does in Python.
CREATE OR REPLACE FUNCTION subscription_next_due_date(
    p_subscription_id UUID,
    p_start_date DATE,
    p_end_date DATE,
    p_cadence TEXT,
    p_today DATE
)
RETURNS DATE
LANGUAGE plpgsql
STABLE
SET search_path = public
AS $$
DECLARE
    v_step INTERVAL := subscription_cadence_step(p_cadence);
    v_scheduled DATE := p_start_date;
    v_previous DATE;
    v_claims_from DATE;
    v_following DATE;
BEGIN
    WHILE v_scheduled < p_today LOOP
        v_scheduled := (v_scheduled + v_step)::DATE;
    END LOOP;

    IF p_end_date IS NOT NULL AND v_scheduled > p_end_date THEN
        RETURN NULL;
    END IF;

    v_previous := (v_scheduled - v_step)::DATE;
    v_claims_from := v_previous + (v_scheduled - v_previous) / 2;

    IF NOT EXISTS (
        SELECT 1 FROM payments
        WHERE subscription_id = p_subscription_id
          AND payment_type = 'expense'
          AND payment_date > v_claims_from
          AND payment_date < p_today
    ) THEN
        RETURN v_scheduled;
    END IF;

    v_following := (v_scheduled + v_step)::DATE;
    IF p_end_date IS NOT NULL AND v_following > p_end_date THEN
        RETURN NULL;
    END IF;
    RETURN v_following;
END;
$$;

-- Write the joint income leg of a written personal expense, then point the expense
-- at it. `linked_payment_id` is a foreign key onto `payments`, so a pair can't be
-- cross-linked in two inserts: the expense goes first, unlinked. Returns the
-- income's id.
CREATE OR REPLACE FUNCTION book_joint_income_leg(
    p_user_id TEXT,
    p_joint_account_id UUID,
    p_expense_id UUID,
    p_name TEXT,
    p_amount DOUBLE PRECISION,
    p_payment_date DATE,
    p_bank_account_id UUID,
    p_income_source_id UUID,
    p_subscription_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_income_id UUID := gen_random_uuid();
BEGIN
    INSERT INTO payments (
        id, user_id, name, income, expense, payment_date, checked, bank_account_id,
        payment_type, subscription_id, income_source_id, linked_payment_id,
        ownership_type, joint_account_id
    ) VALUES (
        v_income_id, p_user_id, p_name, p_amount, 0, p_payment_date, FALSE,
        p_bank_account_id, 'income', p_subscription_id, p_income_source_id,
        p_expense_id, 'joint', p_joint_account_id
    );
    UPDATE payments SET linked_payment_id = v_income_id WHERE id = p_expense_id;
    RETURN v_income_id;
END;
$$;

CREATE OR REPLACE FUNCTION reconcile_subscriptions(
    p_user_id TEXT,
    p_ownership TEXT,
    p_today DATE DEFAULT CURRENT_DATE
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_account UUID;
    v_sub subscriptions%ROWTYPE;
    v_contribution BOOLEAN;
    v_ended BOOLEAN;
    v_superseded UUID[];
    v_next_date DATE;
    v_expense_id UUID;
    v_owed RECORD;
    v_income_id UUID;
BEGIN
    IF p_ownership NOT IN ('personal', 'joint') THEN
        RAISE EXCEPTION 'Unknown ownership: %', p_ownership;
    END IF;

    -- At most one, enforced by one_joint_account_per_user.
    SELECT joint_account_id INTO v_account
    FROM joint_account_members
    WHERE user_id = p_user_id;

    IF p_ownership = 'joint' AND v_account IS NULL THEN
        RETURN;
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended(
        'reconcile_subscriptions:' || CASE
            WHEN p_ownership = 'joint' THEN v_account::TEXT
            ELSE p_user_id
        END,
        0
    ));

    FOR v_sub IN
        SELECT * FROM subscriptions
        WHERE ownership_type = p_ownership
          AND CASE
                WHEN p_ownership = 'joint' THEN joint_account_id = v_account
                ELSE user_id = p_user_id
              END
    LOOP
        v_contribution := v_sub.joint_income_source_id IS NOT NULL;

        -- A contribution with nowhere to book its income waits, untouched, rather
        -- than booking half of itself.
        IF v_contribution AND (p_ownership = 'joint' OR v_account IS NULL) THEN
            CONTINUE;
        END IF;

        v_ended := NOT v_sub.is_active
            OR (v_sub.end_date IS NOT NULL AND v_sub.end_date < p_today);

        SELECT COALESCE(array_agg(id), '{}') INTO v_superseded
        FROM payments
        WHERE subscription_id = v_sub.id
          AND payment_type = 'expense'
          AND ownership_type = p_ownership
          AND payment_date >= p_today
          AND (v_ended OR (v_sub.end_date IS NOT NULL AND payment_date > v_sub.end_date));

        -- Income first: `linked_payment_id` is ON DELETE SET NULL, so deleting only
        -- the expense would strand an income in the shared books.
        IF v_contribution THEN
            DELETE FROM payments
            WHERE payment_type = 'income'
              AND ownership_type = 'joint'
              AND joint_account_id = v_account
              AND subscription_id = v_sub.id
              AND linked_payment_id = ANY (v_superseded);
        END IF;
        DELETE FROM payments WHERE id = ANY (v_superseded);

        IF v_ended THEN
            CONTINUE;
        END IF;

        IF v_contribution THEN
            FOR v_owed IN
                SELECT id, name, expense, payment_date, linked_payment_id
                FROM payments
                WHERE subscription_id = v_sub.id
                  AND payment_type = 'expense'
                  AND ownership_type = p_ownership
                  AND payment_date >= p_today
            LOOP
                SELECT id INTO v_income_id
                FROM payments
                WHERE payment_type = 'income'
                  AND ownership_type = 'joint'
                  AND joint_account_id = v_account
                  AND subscription_id = v_sub.id
                  AND linked_payment_id = v_owed.id
                LIMIT 1;

                IF v_income_id IS NULL THEN
                    PERFORM book_joint_income_leg(
                        p_user_id, v_account, v_owed.id, v_owed.name, v_owed.expense,
                        v_owed.payment_date, v_sub.joint_bank_account_id,
                        v_sub.joint_income_source_id, v_sub.id
                    );
                ELSIF v_owed.linked_payment_id IS DISTINCT FROM v_income_id THEN
                    UPDATE payments SET linked_payment_id = v_income_id WHERE id = v_owed.id;
                END IF;
            END LOOP;
        END IF;

        IF EXISTS (
            SELECT 1 FROM payments
            WHERE subscription_id = v_sub.id
              AND payment_type = 'expense'
              AND ownership_type = p_ownership
              AND payment_date >= p_today
        ) THEN
            CONTINUE;
        END IF;

        v_next_date := subscription_next_due_date(
            v_sub.id, v_sub.start_date, v_sub.end_date, v_sub.cadence, p_today
        );
        IF v_next_date IS NULL THEN
            CONTINUE;
        END IF;

        v_expense_id := gen_random_uuid();
        INSERT INTO payments (
            id, user_id, name, income, expense, payment_date, checked, bank_account_id,
            payment_type, subscription_id, category_id, ownership_type, joint_account_id
        ) VALUES (
            v_expense_id, p_user_id, 'Sub: ' || v_sub.name, 0, v_sub.amount, v_next_date,
            FALSE, v_sub.bank_account_id, 'expense', v_sub.id, v_sub.category_id,
            p_ownership, CASE WHEN p_ownership = 'joint' THEN v_account END
        );

        IF v_contribution THEN
            PERFORM book_joint_income_leg(
                p_user_id, v_account, v_expense_id, 'Sub: ' || v_sub.name, v_sub.amount,
                v_next_date, v_sub.joint_bank_account_id, v_sub.joint_income_source_id,
                v_sub.id
            );
        END IF;
    END LOOP;
END;
$$;

-- PostgREST caches its schema, so a new function needs it reloaded to be callable.
NOTIFY pgrst, 'reload schema';
