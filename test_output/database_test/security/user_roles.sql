-- Create roles
CREATE ROLE readonly;
CREATE ROLE data_editor;
CREATE ROLE admin;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO data_editor;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;

-- Assign roles to users (example)
-- GRANT data_editor TO user1;