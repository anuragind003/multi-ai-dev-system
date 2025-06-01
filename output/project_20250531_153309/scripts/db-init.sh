#!/bin/bash
#
# Script for initial PostgreSQL database setup and seeding for LTFS Offer CDP.
#
# This script automates the process of setting up the necessary database
# and user for the LTFS Offer CDP application. It performs the following actions:
# 1. Checks for the presence of the 'psql' client.
# 2. Configures database connection parameters using environment variables or defaults.
# 3. Creates the application-specific database user if it does not already exist.
# 4. Creates the application database if it does not already exist and assigns ownership
#    to the newly created or existing application user.
# 5. Executes the schema creation SQL script to define tables and other database objects.
# 6. Executes the data seeding SQL script to populate initial data (optional).
#
# Usage:
#   ./scripts/db-init.sh
#
# Environment Variables (optional, sensible defaults provided):
#   DB_HOST             - PostgreSQL host (default: localhost)
#   DB_PORT             - PostgreSQL port (default: 5432)
#   DB_USER             - Application database user (default: cdp_user)
#   DB_PASSWORD         - Application database password (default: cdp_password)
#   DB_NAME             - Application database name (default: cdp_db)
#   PG_SUPERUSER        - PostgreSQL superuser for initial setup (default: postgres)
#   PG_SUPERUSER_PASSWORD - Password for the superuser (optional, if not needed for auth,
#                           e.g., when using .pgpass or peer authentication)
#   SQL_DIR             - Directory containing SQL files (default: ./sql)
#
# Error Handling:
#   The script will exit immediately if any command fails (`set -e`).
#   It will also exit if any unset variables are used (`set -u`).
#   Pipefail ensures that a pipeline's return status is the status of the last command
#   to exit with a non-zero status, or zero if all commands in the pipeline exit successfully.

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# --- Configuration Variables ---
# These variables can be overridden by setting environment variables before running the script.
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-cdp_user}"
DB_PASSWORD="${DB_PASSWORD:-cdp_password}"
DB_NAME="${DB_NAME:-cdp_db}"
PG_SUPERUSER="${PG_SUPERUSER:-postgres}"
PG_SUPERUSER_PASSWORD="${PG_SUPERUSER_PASSWORD:-}" # Default to empty, relies on .pgpass or other auth methods
SQL_DIR="${SQL_DIR:-./sql}" # Assumes SQL files are in a 'sql' directory relative to the project root

# --- Helper Functions ---

# Function to check if the 'psql' command-line client is available.
check_psql() {
    if ! command -v psql &> /dev/null; then
        echo "Error: 'psql' command not found."
        echo "Please ensure PostgreSQL client tools are installed and available in your PATH."
        exit 1
    fi
}

# Function to execute a SQL command as the PostgreSQL superuser.
# It uses PGPASSWORD environment variable for authentication.
execute_as_superuser() {
    local sql_command="$1"
    echo "  -> Executing as superuser: $sql_command"
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres -w -c "$sql_command"
}

# Function to execute a SQL file as the application database user.
# It connects to the application database and uses PGPASSWORD for authentication.
execute_sql_file() {
    local sql_file="$1"
    if [ ! -f "$sql_file" ]; then
        echo "Error: SQL file not found: $sql_file"
        exit 1
    fi
    echo "  -> Executing SQL file: $sql_file"
    PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -w -f "$sql_file"
}

# Function to check if a specific PostgreSQL database exists.
# Returns 0 if exists, 1 otherwise.
database_exists() {
    local db_name="$1"
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres -w -tAc "SELECT 1 FROM pg_database WHERE datname='$db_name'" | grep -q 1
}

# Function to check if a specific PostgreSQL user (role) exists.
# Returns 0 if exists, 1 otherwise.
user_exists() {
    local user_name="$1"
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres -w -tAc "SELECT 1 FROM pg_roles WHERE rolname='$user_name'" | grep -q 1
}

# --- Main Script Logic ---

echo "--- Starting LTFS Offer CDP Database Initialization ---"
echo "-----------------------------------------------------"
echo "Database Host: $DB_HOST"
echo "Database Port: $DB_PORT"
echo "Database Name: $DB_NAME"
echo "Database User: $DB_USER"
echo "SQL Directory: $SQL_DIR"
echo "-----------------------------------------------------"

# 1. Verify psql client availability
echo "Checking for 'psql' client..."
check_psql
echo "'psql' client found."

# 2. Create Database User
echo "Attempting to create database user '$DB_USER'..."
if user_exists "$DB_USER"; then
    echo "User '$DB_USER' already exists. Skipping user creation."
else
    echo "User '$DB_USER' does not exist. Creating user..."
    # The -w flag (no password prompt) requires PGPASSWORD to be set or .pgpass to be configured.
    execute_as_superuser "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    echo "User '$DB_USER' created successfully."
fi

# 3. Create Database
echo "Attempting to create database '$DB_NAME'..."
if database_exists "$DB_NAME"; then
    echo "Database '$DB_NAME' already exists. Skipping database creation."
    # If you need to force a clean slate every time, uncomment the lines below:
    # echo "Dropping existing database '$DB_NAME' for a clean slate..."
    # execute_as_superuser "DROP DATABASE IF EXISTS $DB_NAME;"
    # echo "Creating database '$DB_NAME' and assigning ownership to '$DB_USER'..."
    # execute_as_superuser "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
else
    echo "Database '$DB_NAME' does not exist. Creating database..."
    execute_as_superuser "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "Database '$DB_NAME' created successfully and owned by '$DB_USER'."
fi

# 4. Apply Schema
echo "Applying database schema from '$SQL_DIR/schema.sql'..."
# Ensure the schema.sql file exists before attempting to execute it.
SCHEMA_SQL_FILE="$SQL_DIR/schema.sql"
if [ ! -f "$SCHEMA_SQL_FILE" ]; then
    echo "Error: Schema SQL file not found at '$SCHEMA_SQL_FILE'."
    echo "Please ensure 'schema.sql' is present in the '$SQL_DIR' directory."
    exit 1
fi
execute_sql_file "$SCHEMA_SQL_FILE"
echo "Schema applied successfully."

# 5. Seed Data (Optional)
echo "Attempting to seed initial data from '$SQL_DIR/seed.sql'..."
SEED_SQL_FILE="$SQL_DIR/seed.sql"
if [ -f "$SEED_SQL_FILE" ]; then
    execute_sql_file "$SEED_SQL_FILE"
    echo "Data seeded successfully."
else
    echo "No seed data file found at '$SEED_SQL_FILE'. Skipping data seeding."
fi

echo "-----------------------------------------------------"
echo "--- LTFS Offer CDP Database Initialization Complete ---"
echo "-----------------------------------------------------"