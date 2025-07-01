-- Enable Row Level Security on the users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy for users: Only allow users to see their own data
CREATE POLICY user_data_policy ON users
FOR ALL
USING (id = current_user_id());

-- Function to get the current user ID (assuming authentication system provides this)
CREATE OR REPLACE FUNCTION current_user_id() RETURNS INTEGER AS $$
SELECT current_setting('app.user_id')::integer;
$$ LANGUAGE SQL SECURITY DEFINER;