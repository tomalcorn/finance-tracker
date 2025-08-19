-- Create the PAYMENTS table
CREATE TABLE PAYMENTS (
    id UUID PRIMARY KEY,
    description TEXT,
    income FLOAT,
    expense FLOAT,
    payment_date DATE,
    checked BOOLEAN,
    bank_account_id UUID REFERENCES BANK_ACCOUNTS(id),
    expense_source_id UUID REFERENCES EXPENSE_SOURCES(id),
    income_source_id UUID REFERENCES INCOME_SOURCES(id),
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the BANK_ACCOUNTS table
CREATE TABLE BANK_ACCOUNTS (
    id UUID PRIMARY KEY,
    name TEXT,
    starting_balance FLOAT,
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the EXPENSE_SOURCES table
CREATE TABLE EXPENSE_SOURCES (
    id UUID PRIMARY KEY,
    name TEXT,
    budget FLOAT,
    budget_tracker_ids UUID[],
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the INCOME_SOURCES table
CREATE TABLE INCOME_SOURCES (
    id UUID PRIMARY KEY,
    name TEXT,
    budget_tracker_ids UUID[],
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the BUDGET_TRACKER table
CREATE TABLE BUDGET_TRACKER (
    id UUID PRIMARY KEY,
    name TEXT,
    total_budget FLOAT,
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the FUN_SPENDING table
CREATE TABLE FUN_SPENDING (
    id UUID PRIMARY KEY,
    name TEXT,
    cost FLOAT,
    current_month FLOAT,
    banked FLOAT,
    budget_tracker_id UUID REFERENCES BUDGET_TRACKER(id),
    user_id UUID REFERENCES profiles(id),
    _created_at TIMESTAMP
);

-- Create the profiles table
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    created_at TIMESTAMP
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