-- Example RLS policy for users table
CREATE POLICY users_policy ON users FOR SELECT USING (auth.uid() = id OR id = 1); -- Allow access to own data and ID 1