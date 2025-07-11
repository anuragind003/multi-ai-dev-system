#!/bin/bash
# init_db.sh
# Script to initialize the PostgreSQL database for the V-KYC system.
# This script performs the following steps:
# 1. Creates the database and user if they don't exist.
# 2. Runs Alembic migrations to set up the schema.
# 3. Applies additional indexes.
# 4. Applies stored procedures/functions.
# 5. Applies data validation triggers/functions.
# 6. Inserts seed data.

# --- Configuration ---
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-vkyc_db}"
DB_USER="${DB_USER:-vkyc_user}"
DB_PASSWORD="${DB_PASSWORD:-vkyc_password}" # Use environment variable PGPASSWORD for production

# Path to SQL files
SCHEMA_SQL="./schema.sql" # Used for initial DB creation, Alembic handles schema thereafter
INDEXES_SQL="./indexes.sql"
STORED_PROCEDURES_SQL="./stored_procedures.sql"
DATA_VALIDATION_SQL="./data_validation.sql"
SEED_DATA_SQL="./seed_data.sql"

# Alembic configuration
ALEMBIC_INI="./alembic.ini"
ALEMBIC_DIR="./alembic"

# --- Logging Function ---
log_step() {
    echo "--- $(date +"%Y-%m-%d %H:%M:%S") - $1 ---"
}

# --- Error Handling ---
handle_error() {
    log_step "ERROR: $1"
    exit 1
}

# --- Pre-checks ---
check_dependencies() {
    log_step "Checking dependencies (psql, alembic)..."
    command -v psql >/dev/null 2>&1 || handle_error "psql is not installed. Please install PostgreSQL client."
    command -v alembic >/dev/null 2>&1 || handle_error "alembic is not installed. Please install Alembic (pip install alembic)."
    log_step "Dependencies checked."
}

# --- Create Database and User ---
create_db_and_user() {
    log_step "Attempting to create database '$DB_NAME' and user '$DB_USER'..."

    # Check if user exists
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1
    if [ $? -ne 0 ]; then
        log_step "User '$DB_USER' does not exist. Creating user..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';" || handle_error "Failed to create user '$DB_USER'."
    else
        log_step "User '$DB_USER' already exists."
    fi

    # Check if database exists
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -wq "$DB_NAME"
    if [ $? -ne 0 ]; then
        log_step "Database '$DB_NAME' does not exist. Creating database..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" || handle_error "Failed to create database '$DB_NAME'."
    else
        log_step "Database '$DB_NAME' already exists."
    fi

    log_step "Database and user creation/check complete."
}

# --- Run Alembic Migrations ---
run_alembic_migrations() {
    log_step "Running Alembic migrations..."
    # Ensure alembic.ini points to the correct database URL
    # This assumes alembic.ini is configured to read from environment variables or a config file
    # For this setup, we'll ensure db_config.py is used by alembic's env.py
    export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD # Export for alembic's env.py

    # Initialize Alembic if not already
    if [ ! -d "$ALEMBIC_DIR" ]; then
        log_step "Alembic directory not found. Initializing Alembic..."
        alembic init alembic || handle_error "Failed to initialize Alembic."
        # Copy initial_schema.py to alembic/versions/
        cp ./alembic/versions/initial_schema.py "$ALEMBIC_DIR/versions/" || handle_error "Failed to copy initial_schema.py."
        # Modify alembic.ini to point to the correct script location if needed
        # sed -i '' "s|script_location = .*|script_location = $ALEMBIC_DIR|" "$ALEMBIC_INI" # For macOS
        # sed -i "s|script_location = .*|script_location = $ALEMBIC_DIR|" "$ALEMBIC_INI" # For Linux
        log_step "Alembic initialized. Please ensure alembic/env.py is configured to use db_config.py."
    fi

    # Run migrations
    alembic -c "$ALEMBIC_INI" upgrade head || handle_error "Alembic migration failed."
    log_step "Alembic migrations completed successfully."
}

# --- Apply SQL Scripts ---
apply_sql_script() {
    local script_path="$1"
    local description="$2"
    if [ -f "$script_path" ]; then
        log_step "Applying $description from '$script_path'..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$script_path" || handle_error "Failed to apply $description."
        log_step "$description applied successfully."
    else
        log_step "Skipping $description: '$script_path' not found."
    fi
}

# --- Main Execution ---
log_step "Starting database initialization for V-KYC system..."

check_dependencies
create_db_and_user
run_alembic_migrations # This will create schema, indexes, and triggers defined in initial_schema.py

# The following steps are mostly redundant if Alembic migration handles everything,
# but included for completeness if some elements are managed outside Alembic.
# For this project, initial_schema.py handles schema, indexes, and the vkyc_id trigger.
# Stored procedures and seed data are typically applied after schema is stable.

apply_sql_script "$STORED_PROCEDURES_SQL" "stored procedures and functions"
apply_sql_script "$SEED_DATA_SQL" "seed data"

log_step "Database initialization complete."
echo "To connect to the database: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"