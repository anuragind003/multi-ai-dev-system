-- database_initialization_script.sql
-- Initializes the database, creating the database itself and applying the schema.

-- Connect to the PostgreSQL server as a superuser (e.g., postgres).
-- CREATE DATABASE IF NOT EXISTS postgres; -- Already exists, but good practice to include.

-- Create the database if it doesn't exist.  This is often done manually or by a deployment tool.
-- CREATE DATABASE task_management; -- Removed, as it's assumed the database already exists.

-- Connect to the newly created database.
\c postgres;

-- Apply the schema definition.
\i schema_definition.sql

-- Apply the essential indexes.
\i essential_indexes.sql

-- Apply the stored procedures and functions.
\i stored_procedures_functions.sql

-- Seed the database with initial data.
\i seed_data.sql

-- Grant permissions to the application user (already done in schema_definition.sql, but good to reiterate).
-- GRANT ALL PRIVILEGES ON DATABASE task_management TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;

-- Optionally, analyze the database for query optimization.
ANALYZE;

-- Commit the transaction (if applicable).  Not strictly necessary in this script, but good practice.
-- COMMIT;

-- Display a success message.
SELECT 'Database initialization complete.' AS message;