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
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
);

-- Create the BANK_ACCOUNTS table
CREATE TABLE BANK_ACCOUNTS (
    id UUID PRIMARY KEY,
    name TEXT,
    starting_balance FLOAT,
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
);

-- Create the EXPENSE_SOURCES table
CREATE TABLE EXPENSE_SOURCES (
    id UUID PRIMARY KEY,
    name TEXT,
    budget FLOAT,
    budget_tracker_ids UUID[],
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
);

-- Create the INCOME_SOURCES table
CREATE TABLE INCOME_SOURCES (
    id UUID PRIMARY KEY,
    name TEXT,
    budget_tracker_ids UUID[],
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
);

-- Create the BUDGET_TRACKER table
CREATE TABLE BUDGET_TRACKER (
    id UUID PRIMARY KEY,
    name TEXT,
    total_budget FLOAT,
    user_id UUID REFERENCES USER_INFO(user_id),
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
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
);

-- Create the USER_INFO table
CREATE TABLE USER_INFO (
    user_id UUID PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    created_at TIMESTAMP
);
