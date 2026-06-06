-- Enable Row Level Security (RLS) for all tables and create policies
-- This ensures users can only access and modify their own data

-- Enable RLS on all tables
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE income_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE one_offs ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Create public.user_id() to read Auth0 sub from JWT claims
CREATE OR REPLACE FUNCTION public.user_id() RETURNS TEXT AS $$
  SELECT NULLIF(
    current_setting('request.jwt.claims', true)::json->>'userId',
    ''
  )::TEXT;
$$ LANGUAGE sql STABLE;

-- Create RLS policies for payments table
CREATE POLICY payments_user_policy ON payments
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for bank_accounts table
CREATE POLICY bank_accounts_user_policy ON bank_accounts
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for expense_sources table
CREATE POLICY expense_sources_user_policy ON expense_sources
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for income_sources table
CREATE POLICY income_sources_user_policy ON income_sources
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for budget_tracker table
CREATE POLICY budget_tracker_user_policy ON budget_tracker
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for one_offs table
CREATE POLICY one_offs_user_policy ON one_offs
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Create RLS policies for subscriptions table
CREATE POLICY subscriptions_user_policy ON subscriptions
    FOR ALL
    TO authenticated
    USING (user_id = public.user_id())
    WITH CHECK (user_id = public.user_id());

-- Note: Views automatically inherit RLS from their underlying tables
-- expense_sources_view, income_sources_view, budget_tracker_view, and one_offs_view
-- will automatically filter based on the RLS policies of their underlying tables
-- when accessed by users.
