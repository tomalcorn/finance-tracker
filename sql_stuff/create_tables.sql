-- Create the bank_accounts table
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    starting_balance FLOAT NOT NULL DEFAULT 0,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the expense_sources table
CREATE TABLE expense_sources (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    budget FLOAT NOT NULL DEFAULT 0,
    budget_tracker_ids UUID[],
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the income_sources table
CREATE TABLE income_sources (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    budget_tracker_ids UUID[],
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    income FLOAT NOT NULL DEFAULT 0,
    expense FLOAT NOT NULL DEFAULT 0,
    income_source_id UUID REFERENCES income_sources(id),
    expense_source_id UUID REFERENCES expense_sources(id),
    payment_date DATE,
    checked BOOLEAN,
    bank_account_id UUID REFERENCES bank_accounts(id),
    payment_type TEXT NOT NULL DEFAULT 'expense',
    subscription_id UUID,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);


-- Create the subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    amount FLOAT NOT NULL,
    cadence TEXT NOT NULL,
    bank_account_id UUID REFERENCES bank_accounts(id),
    expense_source_id UUID REFERENCES expense_sources(id),
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Add foreign key from payments to subscriptions
ALTER TABLE payments ADD CONSTRAINT payments_subscription_fk
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE;

-- Create the budget_tracker table
CREATE TABLE budget_tracker (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    total_budget FLOAT NOT NULL DEFAULT 0,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    UNIQUE (user_id, name)
);

-- Create the one_offs table
CREATE TABLE one_offs (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    cost FLOAT,
    current_month FLOAT,
    banked FLOAT,
    budget_tracker_id UUID,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the subscriptions_view view
CREATE OR REPLACE VIEW subscriptions_view WITH (security_invoker = on) AS
SELECT
    s.*,
    CASE s.cadence
        WHEN 'weekly' THEN s.amount * 52.0 / 12.0
        WHEN 'biannually' THEN s.amount / 6.0
        WHEN 'monthly' THEN s.amount
        WHEN 'quarterly' THEN s.amount / 3.0
        WHEN 'yearly' THEN s.amount / 12.0
        ELSE 0
    END AS monthly_cost
FROM subscriptions s;

-- Create the one_offs_view view
CREATE OR REPLACE VIEW one_offs_view WITH (security_invoker = on) AS
SELECT
    fs.id,
    fs.user_id,
    fs.name,
    fs.cost,
    fs.current_month,
    fs.banked,
    fs.budget_tracker_id,
    fs._created_at,
    fs.cost - fs.current_month - fs.banked AS remaining,
    CASE
        WHEN fs.cost > 0
        THEN fs.banked / fs.cost * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(bt_totals.total_budget, 0) > 0
        THEN fs.current_month / bt_totals.total_budget * 100
        ELSE 0
    END AS split
FROM
    one_offs fs
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM budget_tracker bt
    WHERE bt.id = fs.budget_tracker_id
) bt_totals ON TRUE;

-- Create the expense_sources_view view
CREATE OR REPLACE VIEW expense_sources_view WITH (security_invoker = on) AS
SELECT
    es.id,
    es.user_id,
    es.name,
    es.budget,
    COALESCE(SUM(p.expense - p.income), 0) AS current_month,
    es.budget_tracker_ids,
    es._created_at,
    es.budget - COALESCE(SUM(p.expense - p.income), 0) AS remaining,
    CASE
        WHEN es.budget > 0
        THEN COALESCE(SUM(p.expense - p.income), 0) / es.budget * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(bt_totals.total_budget, 0) > 0
        THEN es.budget / bt_totals.total_budget * 100
        ELSE 0
    END AS split
FROM
    expense_sources es
LEFT JOIN
    payments p
ON
    es.id = p.expense_source_id
    AND p.payment_date >= date_trunc('month', CURRENT_DATE)
    AND p.payment_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM budget_tracker bt
    WHERE bt.id = ANY(es.budget_tracker_ids)
) bt_totals ON TRUE
GROUP BY
    es.id, es.user_id, es.name, es.budget, es.budget_tracker_ids, es._created_at, bt_totals.total_budget;

-- Create the income_sources_view view
CREATE OR REPLACE VIEW income_sources_view WITH (security_invoker = on) AS
SELECT
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    COALESCE(SUM(payments.income), 0) AS current_month,
    "income_sources".budget_tracker_ids
FROM
    "income_sources"
LEFT JOIN
    payments
ON
    "income_sources".id = payments.income_source_id
    AND payments.payment_date >= date_trunc('month', CURRENT_DATE)
    AND payments.payment_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY
    "income_sources".id,
    "income_sources".user_id,
    "income_sources".name,
    "income_sources".budget_tracker_ids;

-- Create the budget_tracker_view view
CREATE OR REPLACE VIEW budget_tracker_view WITH (security_invoker = on) AS
SELECT
    bt.id,
    bt.user_id,
    bt.name,
    bt.total_budget,
    bt._created_at,
    COALESCE(SUM(esv.current_month), 0) AS current_month,
    bt.total_budget - COALESCE(SUM(esv.current_month), 0) AS remaining,
    CASE
        WHEN bt.total_budget > 0
        THEN COALESCE(SUM(esv.current_month), 0) / bt.total_budget * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(income_totals.total_income, 0) > 0
        THEN bt.total_budget / income_totals.total_income * 100
        ELSE 0
    END AS split
FROM
    budget_tracker bt
LEFT JOIN
    expense_sources es ON bt.id = ANY(es.budget_tracker_ids)
LEFT JOIN
    expense_sources_view esv ON es.id = esv.id
LEFT JOIN LATERAL (
    SELECT COALESCE(SUM(incv.current_month), 0) AS total_income
    FROM income_sources inc
    JOIN income_sources_view incv ON inc.id = incv.id
    WHERE bt.id = ANY(inc.budget_tracker_ids)
) income_totals ON TRUE
GROUP BY
    bt.id, bt.user_id, bt.name, bt.total_budget, bt._created_at, income_totals.total_income;

-- Create the bank_accounts_view view
CREATE OR REPLACE VIEW bank_accounts_view WITH (security_invoker = on) AS
SELECT
    ba.id,
    ba.user_id,
    ba.name,
    ba.starting_balance,
    ba._created_at,
    ba.starting_balance + COALESCE(SUM(p.income - p.expense), 0) AS current_balance
FROM
    bank_accounts ba
LEFT JOIN
    payments p
ON
    ba.id = p.bank_account_id
    AND p.payment_date <= CURRENT_DATE
GROUP BY
    ba.id,
    ba.user_id,
    ba.name,
    ba.starting_balance,
    ba._created_at;