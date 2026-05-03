-- Enable Row Level Security (RLS) for all tables and create policies
-- This ensures users can only access and modify their own data

-- Enable RLS on all tables
ALTER TABLE PAYMENTS ENABLE ROW LEVEL SECURITY;
ALTER TABLE BANK_ACCOUNTS ENABLE ROW LEVEL SECURITY;
ALTER TABLE EXPENSE_SOURCES ENABLE ROW LEVEL SECURITY;
ALTER TABLE INCOME_SOURCES ENABLE ROW LEVEL SECURITY;
ALTER TABLE BUDGET_TRACKER ENABLE ROW LEVEL SECURITY;
ALTER TABLE ONE_OFFS ENABLE ROW LEVEL SECURITY;
ALTER TABLE SUBSCRIPTIONS ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for PAYMENTS table
CREATE POLICY payments_user_policy ON PAYMENTS
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for BANK_ACCOUNTS table
CREATE POLICY bank_accounts_user_policy ON BANK_ACCOUNTS
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for EXPENSE_SOURCES table
CREATE POLICY expense_sources_user_policy ON EXPENSE_SOURCES
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for INCOME_SOURCES table
CREATE POLICY income_sources_user_policy ON INCOME_SOURCES
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for BUDGET_TRACKER table
CREATE POLICY budget_tracker_user_policy ON BUDGET_TRACKER
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for ONE_OFFS table
CREATE POLICY one_offs_user_policy ON ONE_OFFS
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for SUBSCRIPTIONS table
CREATE POLICY subscriptions_user_policy ON SUBSCRIPTIONS
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Create RLS policies for profiles table
-- Users can only see and modify their own profile
CREATE POLICY profiles_user_policy ON profiles
    FOR ALL
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- Note: Views automatically inherit RLS from their underlying tables
-- EXPENSE_SOURCES_VIEW, income_sources_view, BUDGET_TRACKER_VIEW, and ONE_OFFS_VIEW
-- will automatically filter based on the RLS policies of their underlying tables
-- when accessed by users.

-- Optional: Grant necessary permissions (uncomment if needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
