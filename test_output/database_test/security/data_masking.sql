-- Function to mask email addresses
CREATE OR REPLACE FUNCTION mask_email() RETURNS TEXT AS $$
BEGIN
  RETURN substr(current_setting('user.email'), 1, 2) || '...' || substr(current_setting('user.email'), length(current_setting('user.email')) - 2);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- View to mask email addresses for non-production environments
CREATE VIEW masked_users AS
SELECT id, username, mask_email() AS email, created_at
FROM users;