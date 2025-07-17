#!/bin/bash
# scripts/init_db.sh
# This script initializes the PostgreSQL database for the VKYC Recordings system.
# It performs the following steps:
# 1. Reads database configuration.
# 2. Creates the database and user if they don't exist.
# 3. Runs Alembic migrations to apply the schema.
# 4. Inserts seed data for development/testing.
# 5. Applies additional indexes and stored procedures.
# 6. Applies data validation rules.

# --- Configuration ---
# Load database credentials from config/database.ini
CONFIG_FILE="config/database.ini"
DB_HOST=$(grep -E '^host\s*=' "$CONFIG_FILE" | sed -E 's/host\s*=\s*(.*)/\1/')
DB_PORT=$(grep -E '^port\s*=' "$CONFIG_FILE" | sed -E 's/port\s*=\s*(.*)/\1/')
DB_NAME=$(grep -E '^database\s*=' "$CONFIG_FILE" | sed -E 's/database\s*=\s*(.*)/\1/')
DB_USER=$(grep -E '^user\s*=' "$CONFIG_FILE" | sed -E 's/user\s*=\s*(.*)/\1/')
DB_PASSWORD=$(grep -E '^password\s*=' "$CONFIG_FILE" | sed -E 's/password\s*=\s*(.*)/\1/')

# Set environment variables for psql and alembic
export PGPASSWORD=$DB_PASSWORD
export PGHOST=$DB_HOST
export PGPORT=$DB_PORT
export PGUSER=$DB_USER
export PGDATABASE=$DB_NAME # For alembic, it needs to know the target DB

LOG_FILE="init_db.log"

# --- Functions ---

log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_message "ERROR: '$1' command not found. Please install it and ensure it's in your PATH."
        exit 1
    fi
}

# Check for required commands
check_command "psql"
check_command "alembic"

create_db_and_user() {
    log_message "Attempting to connect to 'postgres' database to create user and database..."
    # Connect to the default 'postgres' database to manage users and databases
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';" 2>> "$LOG_FILE"
    if [ $? -eq 0 ]; then
        log_message "User '$DB_USER' created successfully."
    else
        log_message "User '$DB_USER' might already exist or creation failed. Continuing..."
    fi

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" 2>> "$LOG_FILE"
    if [ $? -eq 0 ]; then
        log_message "Database '$DB_NAME' created successfully."
    else
        log_message "Database '$DB_NAME' might already exist or creation failed. Continuing..."
    fi
}

run_alembic_migrations() {
    log_message "Running Alembic migrations..."
    # Ensure alembic.ini is configured correctly to point to db/migrations
    # For this setup, we assume alembic.ini is in the root or specified via -c
    # If alembic.ini is in the root, just 'alembic upgrade head' works.
    # If it's in a specific path, use 'alembic -c /path/to/alembic.ini upgrade head'
    # Assuming alembic.ini is in the project root, and script_location is set to db/migrations
    alembic upgrade head 2>> "$LOG_FILE"
    if [ $? -eq 0 ]; then
        log_message "Alembic migrations applied successfully."
    else
        log_message "ERROR: Alembic migrations failed. Check '$LOG_FILE' for details."
        exit 1
    fi
}

apply_sql_script() {
    local script_path="$1"
    local script_name=$(basename "$script_path")
    log_message "Applying SQL script: $script_name..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$script_path" 2>> "$LOG_FILE"
    if [ $? -eq 0 ]; then
        log_message "Script '$script_name' applied successfully."
    else
        log_message "ERROR: Script '$script_name' failed. Check '$LOG_FILE' for details."
        exit 1
    fi
}

# --- Main Execution ---
log_message "Starting database initialization for VKYC Recordings system..."

# 1. Create database and user (if not exists)
create_db_and_user

# 2. Run Alembic migrations
run_alembic_migrations

# 3. Apply essential indexes
apply_sql_script "db/indexes.sql"

# 4. Apply stored procedures/functions
apply_sql_script "db/procedures.sql"

# 5. Apply data validation rules (CHECK constraints, etc.)
apply_sql_script "db/data_validation.sql"

# 6. Insert seed data
apply_sql_script "db/seed_data.sql"

log_message "Database initialization complete."

# Unset PGPASSWORD for security
unset PGPASSWORD
unset PGHOST
unset PGPORT
unset PGUSER
unset PGDATABASE