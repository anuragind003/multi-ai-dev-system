-- schema_definition.sql
-- Defines the database schema for the task management system.

-- Create the 'tasks' table.
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Use UUID for unique identifiers.
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(), -- Use TIMESTAMPTZ for timezone-aware timestamps.
    metadata JSONB -- Store additional task-related data in JSON format (emulating document-oriented storage).
);

-- Add a user for the application
CREATE USER app_user WITH PASSWORD 'secure_password'; -- Replace 'secure_password' with a strong password.
GRANT CONNECT ON DATABASE postgres TO app_user; -- Grant connect privilege to the database.
GRANT USAGE ON SCHEMA public TO app_user; -- Grant usage privilege on the public schema.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE tasks TO app_user; -- Grant CRUD privileges on the tasks table.

-- Create a role for database administrators
CREATE ROLE db_admin WITH LOGIN PASSWORD 'admin_password' SUPERUSER; -- Replace 'admin_password' with a strong password.

-- Add a function to generate UUIDs if not already available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: Create a separate schema for application-specific objects (best practice).
-- CREATE SCHEMA IF NOT EXISTS app;
-- ALTER TABLE tasks SET SCHEMA app;
-- GRANT USAGE ON SCHEMA app TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app.tasks TO app_user;