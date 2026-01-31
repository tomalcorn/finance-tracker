# ADR for the joint workflow

Conversation with Claude

## Me

I'm trying to build a finance tracker app. The most granular level is the payments section where individual payments are entered and associated either with an expense source or income source. Those are the next levels. Each expense source is then associated with an entry in the budget tracker (the highest, most zoomed out level). I want the budget tracker to have 4 entries, expenses, one-offs, savings, and joint. You see, I want to share this app with another user. I want to see all of my payments expense sources etc, but not see hers and vice versa. But some portion of my income should go to joint, as should hers. I want a separate page for entering and viewing the payments, expense sources and budget tracker items for the joint, and we should both be able to see those. At the minute here are my SQL statements for the backend (supabase): SQL stuff

## Claude

I need to think through this architecture carefully. You want:

1. **Personal data** - Each user sees only their own payments, expense sources, income sources, and budget tracker
2. **Joint data** - Both users see the same joint payments, expense sources, income sources, and budget tracker
3. **Contribution model** - Each user allocates a portion of their income to joint expenses

Here's my recommended approach:

## Database Schema Changes

### 1. Add a `shared_accounts` table

This manages the relationship between users who share joint finances:

```sql
CREATE TABLE shared_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE shared_account_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shared_account_id UUID REFERENCES shared_accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(shared_account_id, user_id)
);
```

### 2. Add `ownership_type` to your main tables

Modify your existing tables to support both personal and joint ownership:

```sql
-- Add ownership columns to existing tables
ALTER TABLE BUDGET_TRACKER ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE BUDGET_TRACKER ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

ALTER TABLE EXPENSE_SOURCES ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE EXPENSE_SOURCES ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

ALTER TABLE INCOME_SOURCES ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE INCOME_SOURCES ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

ALTER TABLE PAYMENTS ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE PAYMENTS ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

ALTER TABLE BANK_ACCOUNTS ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE BANK_ACCOUNTS ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

ALTER TABLE FUN_SPENDING ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal';
ALTER TABLE FUN_SPENDING ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);
```

### 3. Create a joint contribution tracking table

Track how much each user contributes to joint expenses:

```sql
CREATE TABLE joint_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    shared_account_id UUID REFERENCES shared_accounts(id),
    income_source_id UUID REFERENCES INCOME_SOURCES(id),
    amount FLOAT,
    percentage FLOAT, -- Alternative to fixed amount
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_amount_or_percentage CHECK (
        (amount IS NOT NULL AND percentage IS NULL) OR 
        (amount IS NULL AND percentage IS NOT NULL)
    )
);
```

### 4. Update RLS Policies

```sql
-- Drop existing policies
DROP POLICY IF EXISTS payments_user_policy ON PAYMENTS;
DROP POLICY IF EXISTS bank_accounts_user_policy ON BANK_ACCOUNTS;
DROP POLICY IF EXISTS expense_sources_user_policy ON EXPENSE_SOURCES;
DROP POLICY IF EXISTS income_sources_user_policy ON INCOME_SOURCES;
DROP POLICY IF EXISTS budget_tracker_user_policy ON BUDGET_TRACKER;
DROP POLICY IF EXISTS fun_spending_user_policy ON FUN_SPENDING;

-- PAYMENTS policies
CREATE POLICY payments_user_policy ON PAYMENTS
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- BANK_ACCOUNTS policies
CREATE POLICY bank_accounts_user_policy ON BANK_ACCOUNTS
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- EXPENSE_SOURCES policies
CREATE POLICY expense_sources_user_policy ON EXPENSE_SOURCES
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- INCOME_SOURCES policies
CREATE POLICY income_sources_user_policy ON INCOME_SOURCES
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- BUDGET_TRACKER policies
CREATE POLICY budget_tracker_user_policy ON BUDGET_TRACKER
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- FUN_SPENDING policies
CREATE POLICY fun_spending_user_policy ON FUN_SPENDING
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    ))
);

-- Shared accounts RLS
ALTER TABLE shared_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared_account_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE joint_contributions ENABLE ROW LEVEL SECURITY;

CREATE POLICY shared_accounts_member_policy ON shared_accounts
FOR ALL TO authenticated
USING (id IN (SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()))
WITH CHECK (id IN (SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()));

CREATE POLICY shared_account_members_policy ON shared_account_members
FOR ALL TO authenticated
USING (user_id = auth.uid() OR shared_account_id IN (
    SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
))
WITH CHECK (user_id = auth.uid() OR shared_account_id IN (
    SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
));

CREATE POLICY joint_contributions_policy ON joint_contributions
FOR ALL TO authenticated
USING (
    user_id = auth.uid() OR shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    )
)
WITH CHECK (
    user_id = auth.uid() OR shared_account_id IN (
        SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
    )
);
```

## Frontend/App Structure

1. **Personal Dashboard** - Shows only `ownership_type = 'personal'` data
2. **Joint Dashboard** - Shows only `ownership_type = 'joint'` data where user is a member
3. **Navigation** - Toggle or separate pages for Personal vs Joint views

## How It Works

1. When you create personal budget tracker entries, set `ownership_type = 'personal'` and `user_id = your_id`
2. When creating joint entries, set `ownership_type = 'joint'`, `shared_account_id = shared_account_id`, and `user_id` can be null or set to whoever created it
3. The RLS policies ensure each user only sees their personal data + any joint data from shared accounts they're members of

Does this approach make sense for your use case? Would you like me to clarify any part or discuss alternative approaches?

## Me 2

How does the joint contribution table work? What might a typical month look like?

## Claude 2

Great question! Let me walk through a typical month to show how the joint contribution system would work.

## Typical Month Scenario

**Setup:**

- You earn $5,000/month from your job
- Your partner earns $4,000/month from their job
- You've agreed to each contribute to joint expenses

### Option 1: Percentage-based contributions

```sql
-- Your contribution: 60% of your income goes to joint
INSERT INTO joint_contributions (
    user_id, 
    shared_account_id, 
    income_source_id, -- references your "Salary" income source
    percentage,
    amount
) VALUES (
    'your-user-id',
    'shared-account-id',
    'your-salary-income-source-id',
    60.0,  -- 60% of income
    NULL
);

-- Partner's contribution: 60% of their income goes to joint
INSERT INTO joint_contributions (
    user_id, 
    shared_account_id, 
    income_source_id, -- references partner's "Salary" income source
    percentage,
    amount
) VALUES (
    'partner-user-id',
    'shared-account-id',
    'partner-salary-income-source-id',
    60.0,  -- 60% of income
    NULL
);
```

**Result for the month:**

- You contribute: $5,000 × 60% = **$3,000 to joint**
- Partner contributes: $4,000 × 60% = **$2,400 to joint**
- **Total joint pool: $5,400**
- You keep personally: $2,000
- Partner keeps personally: $1,600

### Option 2: Fixed amount contributions

```sql
-- You contribute fixed $3,000
INSERT INTO joint_contributions (
    user_id, 
    shared_account_id, 
    income_source_id,
    percentage,
    amount
) VALUES (
    'your-user-id',
    'shared-account-id',
    'your-salary-income-source-id',
    NULL,
    3000.00  -- Fixed amount
);

-- Partner contributes fixed $2,500
INSERT INTO joint_contributions (
    user_id, 
    shared_account_id, 
    income_source_id,
    percentage,
    amount
) VALUES (
    'partner-user-id',
    'shared-account-id',
    'partner-salary-income-source-id',
    NULL,
    2500.00
);
```

**Result for the month:**

- You contribute: **$3,000 to joint**
- Partner contributes: **$2,500 to joint**
- **Total joint pool: $5,500**
- You keep personally: $2,000
- Partner keeps personally: $1,500

## How This Flows Through Your System

### 1. **Income Sources**

**Your Personal Income Sources:**

```
- Salary (personal, ownership_type='personal')
  - Total: $5,000
  - Joint contribution: -$3,000 (calculated from joint_contributions)
  - Available for personal expenses: $2,000
```

**Joint Income Sources:**

```
- Combined Contributions (joint, ownership_type='joint')
  - Your contribution: $3,000
  - Partner's contribution: $2,500
  - Total: $5,500
```

### 2. **Budget Tracker Entries**

**Your Personal Budget:**

```
- Expenses: $1,500 (groceries, gas, personal subscriptions)
- One-offs: $300 (clothes, hobbies)
- Savings: $200
- Total: $2,000 (matches your remaining income)
```

**Joint Budget (both see this):**

```
- Expenses: $4,000 (rent, utilities, joint car payment)
- One-offs: $500 (furniture, household items)
- Savings: $1,000 (joint emergency fund)
- Joint: N/A (this category doesn't exist in joint budget)
- Total: $5,500
```

### 3. **Payments Flow**

**Your personal payments:**

```sql
-- Personal grocery shopping
INSERT INTO PAYMENTS (
    user_id,
    name,
    expense,
    expense_source_id,  -- links to your personal "Groceries" expense source
    ownership_type,
    payment_date,
    bank_account_id
) VALUES (
    'your-user-id',
    'Whole Foods',
    150.00,
    'personal-groceries-expense-source-id',
    'personal',
    '2026-01-15',
    'your-personal-bank-account-id'
);
```

**Joint payments (either of you can enter):**

```sql
-- Rent payment
INSERT INTO PAYMENTS (
    user_id,  -- whoever entered it
    name,
    expense,
    expense_source_id,  -- links to joint "Housing" expense source
    ownership_type,
    shared_account_id,
    payment_date,
    bank_account_id  -- joint bank account
) VALUES (
    'your-user-id',  -- you entered it, but partner can see it
    'Rent - January',
    2500.00,
    'joint-housing-expense-source-id',
    'joint',
    'shared-account-id',
    '2026-01-01',
    'joint-bank-account-id'
);
```

## Visualization Helper View

You might want to create a view to easily see joint contributions:

```sql
CREATE OR REPLACE VIEW joint_contribution_summary AS
SELECT 
    jc.shared_account_id,
    jc.user_id,
    u.first_name,
    u.last_name,
    jc.income_source_id,
    is_view.name AS income_source_name,
    jc.amount AS fixed_amount,
    jc.percentage,
    CASE 
        WHEN jc.percentage IS NOT NULL 
        THEN is_view.current_month * (jc.percentage / 100)
        ELSE jc.amount
    END AS calculated_contribution,
    is_view.current_month AS total_income
FROM 
    joint_contributions jc
JOIN 
    users u ON jc.user_id = u.id
LEFT JOIN 
    income_sources_view is_view ON jc.income_source_id = is_view.id;
```

This view would show:

```
| User          | Income Source | Total Income | Contribution Type | Contribution Amount |
|---------------|---------------|--------------|-------------------|---------------------|
| You           | Salary        | $5,000       | 60%               | $3,000              |
| Partner       | Salary        | $4,000       | 60%               | $2,400              |
| **JOINT TOTAL**                                                   | **$5,400**          |
```

## Questions to Consider

1. **Do you want automatic transfers?** Should the system automatically create a "payment" that transfers money from personal income to joint when payday hits?

2. **Multiple income sources?** What if you have a side hustle? Do you contribute from that too, or only from primary income?

3. **Variable income?** Percentage is better for freelancers/variable income, fixed amount for stable salaries.

4. **Contribution history?** Do you want to track if contributions change over time (e.g., started at 50%, now 60%)?

Would you like me to elaborate on any of these scenarios or help you design the UI flow for managing these contributions?

## Me 3

We'll stick to fixed contributions. But I'm trying to figure out how the contribution bit will work. Should it be an expense source? Will I add a payment called to joint? What would you recommend?

## Claude 3

Great question! Let me think through the options with you.

## Recommended Approach: Joint Contribution as an Expense Source

I think the cleanest approach is to treat your joint contribution as a **personal expense source**. Here's why and how:

### The Flow

**Your Personal Side:**

```sql
-- You have an expense source called "Joint Contribution"
INSERT INTO EXPENSE_SOURCES (
    user_id,
    name,
    budget,
    ownership_type
) VALUES (
    'your-user-id',
    'Joint Contribution',
    3000.00,  -- Your monthly contribution
    'personal'
);

-- Each month (or when you get paid), you create a payment
INSERT INTO PAYMENTS (
    user_id,
    name,
    expense,
    expense_source_id,  -- links to your "Joint Contribution" expense source
    ownership_type,
    payment_date,
    bank_account_id  -- your personal bank account
) VALUES (
    'your-user-id',
    'Transfer to Joint Account',
    3000.00,
    'joint-contribution-expense-source-id',
    'personal',
    '2026-01-31',
    'your-personal-bank-account-id'
);
```

**Joint Side:**

```sql
-- There's a joint income source called "Contributions" or "Monthly Funding"
INSERT INTO INCOME_SOURCES (
    user_id,  -- could be null or whoever set it up
    name,
    ownership_type,
    shared_account_id
) VALUES (
    NULL,  -- or 'your-user-id'
    'Monthly Contributions',
    'joint',
    'shared-account-id'
);

-- You create a matching income payment on the joint side
INSERT INTO PAYMENTS (
    user_id,
    name,
    income,
    income_source_id,  -- links to joint "Monthly Contributions" income source
    ownership_type,
    shared_account_id,
    payment_date,
    bank_account_id  -- joint bank account
) VALUES (
    'your-user-id',  -- you made this transfer
    'Your Name - January Contribution',
    3000.00,
    'joint-contributions-income-source-id',
    'joint',
    'shared-account-id',
    '2026-01-31',
    'joint-bank-account-id'
);
```

**Partner does the same thing from their side.**

### What It Looks Like

**Your Personal Budget Tracker:**

```
Income Sources:
  - Salary: $5,000

Expense Sources:
  - Groceries: $500 / $500 budget
  - Gas: $200 / $200 budget
  - Personal Fun: $300 / $300 budget
  - Joint Contribution: $3,000 / $3,000 budget  ← This is your contribution
  - Savings: $1,000 / $1,000 budget
  
Total: $5,000 in, $5,000 out ✓
```

**Joint Budget Tracker (both see this):**

```
Income Sources:
  - Monthly Contributions: $5,500
    • Your Name: $3,000
    • Partner Name: $2,500

Expense Sources:
  - Rent: $2,500 / $2,500 budget
  - Utilities: $300 / $400 budget
  - Groceries (joint): $800 / $800 budget
  - Joint Car Payment: $400 / $400 budget
  - Joint Savings: $1,500 / $1,500 budget
  
Total: $5,500 in, $5,500 out ✓
```

## Simplified Alternative: Skip the joint_contributions Table

Actually, now that I think about it, you might not even need the `joint_contributions` table at all! Here's why:

1. Your contribution is just a **personal expense source** with a budget
2. That money becomes **joint income** when you transfer it
3. You can see how much each person contributes by looking at the joint income payments

### Updated Schema (Simpler)

You can **remove** the `joint_contributions` table entirely and just use:

- **Personal side**: Expense source called "Joint Contribution" or "To Joint Account"
- **Joint side**: Income source called "Contributions" that shows all incoming transfers

The payments themselves tell the story of who contributed what.

## UI Flow Example

**When you get paid:**

1. **Personal page**: Click "Add Payment"
   - Name: "Paycheck - January"
   - Income: $5,000
   - Income Source: Salary
   - Bank Account: Your Personal Checking

2. **Personal page**: Click "Add Payment" (transfer to joint)
   - Name: "Transfer to Joint"
   - Expense: $3,000
   - Expense Source: Joint Contribution
   - Bank Account: Your Personal Checking

3. **Joint page**: Click "Add Payment"
   - Name: "[Your Name] - January Contribution"
   - Income: $3,000
   - Income Source: Monthly Contributions
   - Bank Account: Joint Checking

**Result:**

- Your personal checking: $5,000 - $3,000 = $2,000 remaining
- Joint checking: +$3,000 from you
- When partner does the same: Joint checking has $5,500 total

## Pro Tip: Link the Payments

You could add a `linked_payment_id` column to help track the transfer:

```sql
ALTER TABLE PAYMENTS ADD COLUMN linked_payment_id UUID REFERENCES PAYMENTS(id);
```

Then when you create the joint income payment, set `linked_payment_id` to reference your personal expense payment. This creates a clear audit trail showing the money moved from personal → joint.

## What Do You Think?

Does treating the contribution as a personal expense source make sense? It keeps things simple and uses your existing structure without needing the extra `joint_contributions` table.

The key insight: **Your contribution to joint is an expense from your perspective, and income from the joint account's perspective.**

## Me 4

So how do I set up an RLS policy to view my data and joint data? What new tables or policies do I need to add to my existing workflow

## Claude 4

Great question! Let me break down exactly what you need to add to your existing setup.

## New Tables Needed

You only need these two tables to enable the joint functionality:

```sql
-- Table to represent a shared account between users
CREATE TABLE shared_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table to track which users belong to which shared accounts
CREATE TABLE shared_account_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shared_account_id UUID REFERENCES shared_accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(shared_account_id, user_id)
);

-- Enable RLS
ALTER TABLE shared_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared_account_members ENABLE ROW LEVEL SECURITY;

-- RLS policies for shared_accounts
-- Users can only see shared accounts they're members of
CREATE POLICY shared_accounts_member_policy ON shared_accounts
FOR ALL TO authenticated
USING (
    id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    )
)
WITH CHECK (
    id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    )
);

-- RLS policies for shared_account_members
-- Users can see membership info for shared accounts they belong to
CREATE POLICY shared_account_members_policy ON shared_account_members
FOR ALL TO authenticated
USING (
    user_id = auth.uid() OR 
    shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    )
)
WITH CHECK (
    user_id = auth.uid() OR 
    shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    )
);
```

## Modify Existing Tables

Add these columns to your existing tables:

```sql
-- Add ownership columns to BUDGET_TRACKER
ALTER TABLE BUDGET_TRACKER 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

-- Add ownership columns to EXPENSE_SOURCES
ALTER TABLE EXPENSE_SOURCES 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

-- Add ownership columns to INCOME_SOURCES
ALTER TABLE INCOME_SOURCES 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

-- Add ownership columns to PAYMENTS
ALTER TABLE PAYMENTS 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

-- Add ownership columns to BANK_ACCOUNTS
ALTER TABLE BANK_ACCOUNTS 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);

-- Add ownership columns to FUN_SPENDING
ALTER TABLE FUN_SPENDING 
ADD COLUMN ownership_type TEXT CHECK (ownership_type IN ('personal', 'joint')) DEFAULT 'personal',
ADD COLUMN shared_account_id UUID REFERENCES shared_accounts(id);
```

## Update Your RLS Policies

Drop the old policies and create new ones that handle both personal and joint data:

```sql
-- ============================================
-- PAYMENTS
-- ============================================
DROP POLICY IF EXISTS payments_user_policy ON PAYMENTS;

CREATE POLICY payments_user_policy ON PAYMENTS
FOR ALL TO authenticated
USING (
    -- User can see their own personal payments
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    -- User can see joint payments from shared accounts they're a member of
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);

-- ============================================
-- BANK_ACCOUNTS
-- ============================================
DROP POLICY IF EXISTS bank_accounts_user_policy ON BANK_ACCOUNTS;

CREATE POLICY bank_accounts_user_policy ON BANK_ACCOUNTS
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);

-- ============================================
-- EXPENSE_SOURCES
-- ============================================
DROP POLICY IF EXISTS expense_sources_user_policy ON EXPENSE_SOURCES;

CREATE POLICY expense_sources_user_policy ON EXPENSE_SOURCES
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);

-- ============================================
-- INCOME_SOURCES
-- ============================================
DROP POLICY IF EXISTS income_sources_user_policy ON INCOME_SOURCES;

CREATE POLICY income_sources_user_policy ON INCOME_SOURCES
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);

-- ============================================
-- BUDGET_TRACKER
-- ============================================
DROP POLICY IF EXISTS budget_tracker_user_policy ON BUDGET_TRACKER;

CREATE POLICY budget_tracker_user_policy ON BUDGET_TRACKER
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);

-- ============================================
-- FUN_SPENDING
-- ============================================
DROP POLICY IF EXISTS fun_spending_user_policy ON FUN_SPENDING;

CREATE POLICY fun_spending_user_policy ON FUN_SPENDING
FOR ALL TO authenticated
USING (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
)
WITH CHECK (
    (ownership_type = 'personal' AND user_id = auth.uid()) 
    OR 
    (ownership_type = 'joint' AND shared_account_id IN (
        SELECT shared_account_id 
        FROM shared_account_members 
        WHERE user_id = auth.uid()
    ))
);
```

## Initial Setup (One-Time)

After running the above, you'll need to set up the shared account:

```sql
-- 1. Create the shared account (run this once)
INSERT INTO shared_accounts (name) 
VALUES ('Our Joint Account') 
RETURNING id;  -- Save this ID!

-- 2. Add both users as members (replace the IDs with actual values)
INSERT INTO shared_account_members (shared_account_id, user_id) 
VALUES 
    ('shared-account-id-from-step-1', 'your-user-id'),
    ('shared-account-id-from-step-1', 'partner-user-id');
```

## How It Works in Practice

### Creating Personal Data (Nothing Changes)

```sql
-- Your personal expense source - works exactly as before
INSERT INTO EXPENSE_SOURCES (user_id, name, budget, ownership_type)
VALUES (auth.uid(), 'Groceries', 500.00, 'personal');
-- ownership_type defaults to 'personal', shared_account_id is NULL
```

### Creating Joint Data (New)

```sql
-- Joint expense source - both you and partner can see this
INSERT INTO EXPENSE_SOURCES (user_id, name, budget, ownership_type, shared_account_id)
VALUES (auth.uid(), 'Rent', 2500.00, 'joint', 'your-shared-account-id');
-- Must specify ownership_type='joint' and shared_account_id
```

### Querying Data (From Your App)

```javascript
// Get all expense sources (personal + joint)
// RLS automatically filters to show only what you can see
const { data: allExpenseSources } = await supabase
    .from('EXPENSE_SOURCES')
    .select('*');
// Returns: Your personal sources + joint sources from shared accounts

// Get ONLY personal expense sources
const { data: personalSources } = await supabase
    .from('EXPENSE_SOURCES')
    .select('*')
    .eq('ownership_type', 'personal');

// Get ONLY joint expense sources
const { data: jointSources } = await supabase
    .from('EXPENSE_SOURCES')
    .select('*')
    .eq('ownership_type', 'joint');
```

## Summary of What Changed

**New tables:**

- `shared_accounts` - represents the joint account
- `shared_account_members` - links users to shared accounts

**Modified existing tables:**

- Added `ownership_type` column (personal/joint)
- Added `shared_account_id` column (NULL for personal, set for joint)

**Updated RLS policies:**

- Now check BOTH `user_id = auth.uid()` (for personal) AND membership in shared accounts (for joint)

**The magic:** RLS automatically shows you the right data. You don't need to manually filter in your app—just query normally and Postgres handles it!

Does this make sense? Want me to clarify any part?
