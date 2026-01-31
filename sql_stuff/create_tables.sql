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
    income FLOAT,
    expense FLOAT,
    income_source_id UUID REFERENCES INCOME_SOURCES(id),
    expense_source_id UUID REFERENCES EXPENSE_SOURCES(id),
    payment_date DATE,
    checked BOOLEAN,
    bank_account_id UUID REFERENCES BANK_ACCOUNTS(id),
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

-- Create the FUN_SPENDING table
CREATE TABLE FUN_SPENDING (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT,
    cost FLOAT,
    current_month FLOAT,
    banked FLOAT,
    budget_tracker_id UUID REFERENCES BUDGET_TRACKER(id),
    _created_at TIMESTAMP
);

-- Create the EXPENSE_SOURCES_VIEW view
CREATE OR REPLACE VIEW EXPENSE_SOURCES_VIEW AS
SELECT
    es.id,
    es.name,
    es.budget,
    COALESCE(SUM(p.income - p.expense), 0) AS current_month,
    es.budget_tracker_ids,
    es._created_at
FROM
    EXPENSE_SOURCES es
LEFT JOIN
    PAYMENTS p
ON
    es.id = p.expense_source_id
GROUP BY
    es.id, es.name, es.budget, es.budget_tracker_ids, es._created_at;

-- Create the income_sources_view view
CREATE OR REPLACE VIEW income_sources_view AS
SELECT
    "income_sources".id,
    "income_sources".name,
    COALESCE(SUM(payments.income - payments.expense), 0) AS current_month,
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
    COALESCE(SUM(esv.current_month), 0) AS current_month
FROM
    BUDGET_TRACKER bt
LEFT JOIN
    EXPENSE_SOURCES es ON bt.id = ANY(es.budget_tracker_ids)
LEFT JOIN
    EXPENSE_SOURCES_VIEW esv ON es.id = esv.id
LEFT JOIN
    INCOME_SOURCES inc ON bt.id = ANY(inc.budget_tracker_ids)
LEFT JOIN
    INCOME_SOURCES_VIEW incv ON inc.id = incv.id
GROUP BY
    bt.id, bt.name, bt.total_budget, bt._created_at;

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