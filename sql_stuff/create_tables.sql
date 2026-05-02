-- Create the users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    first_name TEXT,
    last_name TEXT
);

-- Create the BANK_ACCOUNTS table
CREATE TABLE BANK_ACCOUNTS (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    starting_balance FLOAT,
    _created_at TIMESTAMP
);

-- Create the EXPENSE_SOURCES table
CREATE TABLE EXPENSE_SOURCES (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    budget FLOAT,
    budget_tracker_ids UUID[],
    _created_at TIMESTAMP
);

-- Create the INCOME_SOURCES table
CREATE TABLE INCOME_SOURCES (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    budget_tracker_ids UUID[],
    _created_at TIMESTAMP
);

-- Create the PAYMENTS table
CREATE TABLE PAYMENTS (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    income FLOAT NOT NULL DEFAULT 0,
    expense FLOAT NOT NULL DEFAULT 0,
    income_source_id UUID REFERENCES INCOME_SOURCES(id),
    expense_source_id UUID REFERENCES EXPENSE_SOURCES(id),
    payment_date DATE,
    checked BOOLEAN,
    bank_account_id UUID REFERENCES BANK_ACCOUNTS(id),
    payment_type TEXT NOT NULL DEFAULT 'expense',
    _created_at TIMESTAMP
);


-- Create the BUDGET_TRACKER table
CREATE TABLE BUDGET_TRACKER (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    total_budget FLOAT,
    _created_at TIMESTAMP
);

-- Create the ONE_OFFS table
CREATE TABLE ONE_OFFS (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    cost FLOAT,
    current_month FLOAT,
    banked FLOAT,
    budget_tracker_id UUID,
    _created_at TIMESTAMP
);

-- Create the ONE_OFFS_VIEW view
CREATE OR REPLACE VIEW ONE_OFFS_VIEW AS
SELECT
    fs.id,
    fs.name,
    fs.cost,
    fs.current_month,
    fs.banked,
    fs.budget_tracker_id,
    fs._created_at,
    fs.cost - fs.current_month - fs.banked AS remaining,
    CASE
        WHEN fs.cost > 0
        THEN (fs.current_month + fs.banked) / fs.cost * 100
        ELSE 0
    END AS progress,
    CASE
        WHEN COALESCE(bt_totals.total_budget, 0) > 0
        THEN fs.cost / bt_totals.total_budget * 100
        ELSE 0
    END AS split
FROM
    ONE_OFFS fs
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM BUDGET_TRACKER bt
    WHERE bt.id = fs.budget_tracker_id
) bt_totals ON TRUE;

-- Create the EXPENSE_SOURCES_VIEW view
CREATE OR REPLACE VIEW EXPENSE_SOURCES_VIEW AS
SELECT
    es.id,
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
    EXPENSE_SOURCES es
LEFT JOIN
    PAYMENTS p
ON
    es.id = p.expense_source_id
LEFT JOIN LATERAL (
    SELECT SUM(bt.total_budget) AS total_budget
    FROM BUDGET_TRACKER bt
    WHERE bt.id = ANY(es.budget_tracker_ids)
) bt_totals ON TRUE
GROUP BY
    es.id, es.name, es.budget, es.budget_tracker_ids, es._created_at, bt_totals.total_budget;

-- Create the income_sources_view view
CREATE OR REPLACE VIEW income_sources_view AS
SELECT
    "income_sources".id,
    "income_sources".name,
    COALESCE(SUM(payments.income), 0) AS current_month,
    "income_sources".budget_tracker_ids
FROM
    "income_sources"
LEFT JOIN
    payments
ON
    "income_sources".id = payments.income_source_id
GROUP BY
    "income_sources".id, 
    "income_sources".name, 
    "income_sources".budget_tracker_ids;

-- Create the BUDGET_TRACKER_VIEW view
CREATE OR REPLACE VIEW BUDGET_TRACKER_VIEW AS
SELECT
    bt.id,
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
    END AS props
FROM
    BUDGET_TRACKER bt
LEFT JOIN
    EXPENSE_SOURCES es ON bt.id = ANY(es.budget_tracker_ids)
LEFT JOIN
    EXPENSE_SOURCES_VIEW esv ON es.id = esv.id
LEFT JOIN LATERAL (
    SELECT COALESCE(SUM(incv.current_month), 0) AS total_income
    FROM INCOME_SOURCES inc
    JOIN INCOME_SOURCES_VIEW incv ON inc.id = incv.id
    WHERE bt.id = ANY(inc.budget_tracker_ids)
) income_totals ON TRUE
GROUP BY
    bt.id, bt.name, bt.total_budget, bt._created_at, income_totals.total_income;

-- Create the BANK_ACCOUNTS_VIEW view
CREATE OR REPLACE VIEW BANK_ACCOUNTS_VIEW AS
SELECT
    ba.id,
    ba.user_id,
    ba.name,
    ba.starting_balance,
    ba._created_at,
    ba.starting_balance + COALESCE(SUM(p.income - p.expense), 0) AS current_balance
FROM
    BANK_ACCOUNTS ba
LEFT JOIN
    PAYMENTS p
ON
    ba.id = p.bank_account_id
GROUP BY
    ba.id,
    ba.user_id,
    ba.name,
    ba.starting_balance,
    ba._created_at;