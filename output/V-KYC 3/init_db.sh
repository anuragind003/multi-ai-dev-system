#!/bin/bash
# init_db.sh
# Comprehensive script to initialize the PostgreSQL database system.
# This script will:
# 1. Create the database and user if they don't exist.
# 2. Run Alembic migrations to set up the schema.
# 3. Apply essential indexes.
# 4. Apply stored procedures/functions.
# 5. Seed initial data.

# --- Configuration ---
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="vkyc_db"
DB_USER="vkyc_user"
# DB_PASSWORD should be set as an environment variable for security
# export DB_PASSWORD="your_strong_password_here"
ADMIN_USER="postgres" # PostgreSQL superuser for initial setup
ADMIN_PASSWORD="${PG_ADMIN_PASSWORD}" # Admin password, set as env var

LOG_FILE="./logs/init_db.log"
SCHEMA_FILE="./schema.sql"
INDEXES_FILE="./indexes.sql"
STORED_PROCEDURES_FILE="./stored_procedures.sql"
SEED_DATA_FILE="./seed_data.sql"
ALEMBIC_CONFIG="./alembic.ini" # Assuming alembic.ini is in the root

# Ensure log directory exists
mkdir -p ./logs

# --- Functions ---

log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

check_prerequisites() {
    log_message "Checking prerequisites..."
    command -v psql >/dev/null 2>&1 || { log_message "ERROR: psql command not found. Please install PostgreSQL client tools."; exit 1; }
    command -v alembic >/dev/null 2>&1 || { log_message "ERROR: alembic command not found. Please install Alembic (pip install alembic)."; exit 1; }
    log_message "Prerequisites checked successfully."
}

create_db_and_user() {
    log_message "Attempting to create database '${DB_NAME}' and user '${DB_USER}'..."

    if [ -z "${ADMIN_PASSWORD}" ]; then
        log_message "ERROR: PG_ADMIN_PASSWORD environment variable not set. Cannot connect as admin user."
        exit 1
    fi

    export PGPASSWORD="${ADMIN_PASSWORD}"

    # Check if database exists
    DB_EXISTS=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${ADMIN_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null)
    if [ "$DB_EXISTS" = "1" ]; then
        log_message "Database '${DB_NAME}' already exists. Skipping creation."
    else
        log_message "Creating database '${DB_NAME}'..."
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${ADMIN_USER}" -d postgres -c "CREATE DATABASE \"${DB_NAME}\";" 2>> "${LOG_FILE}"
        if [ $? -ne 0 ]; then
            log_message "ERROR: Failed to create database '${DB_NAME}'. Check PostgreSQL server status and admin credentials."
            exit 1
        fi
        log_message "Database '${DB_NAME}' created."
    fi

    # Check if user exists
    USER_EXISTS=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${ADMIN_USER}" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" 2>/dev/null)
    if [ "$USER_EXISTS" = "1" ]; then
        log_message "User '${DB_USER}' already exists. Skipping creation."
    else
        if [ -z "${DB_PASSWORD}" ]; then
            log_message "ERROR: DB_PASSWORD environment variable not set. Cannot create database user."
            exit 1
        fi
        log_message "Creating user '${DB_USER}'..."
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${ADMIN_USER}" -d postgres -c "CREATE USER \"${DB_USER}\" WITH ENCRYPTED PASSWORD '${DB_PASSWORD}';" 2>> "${LOG_FILE}"
        if [ $? -ne 0 ]; then
            log_message "ERROR: Failed to create user '${DB_USER}'."
            exit 1
        fi
        log_message "User '${DB_USER}' created."
    fi

    # Grant privileges
    log_message "Granting privileges to user '${DB_USER}' on database '${DB_NAME}'..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${ADMIN_USER}" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" TO \"${DB_USER}\";" 2>> "${LOG_FILE}"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to grant privileges."
        exit 1
    fi
    log_message "Privileges granted."

    unset PGPASSWORD # Unset admin password
}

run_alembic_migrations() {
    log_message "Running Alembic migrations..."
    export PGPASSWORD="${DB_PASSWORD}" # Set password for Alembic
    alembic -c "${ALEMBIC_CONFIG}" upgrade head 2>> "${LOG_FILE}"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Alembic migrations failed."
        unset PGPASSWORD
        exit 1
    fi
    log_message "Alembic migrations completed successfully."
    unset PGPASSWORD
}

apply_sql_script() {
    local script_path="$1"
    local script_name=$(basename "$script_path")

    if [ ! -f "${script_path}" ]; then
        log_message "WARNING: SQL script not found: ${script_path}. Skipping."
        return 0
    fi

    log_message "Applying SQL script: ${script_name}..."
    export PGPASSWORD="${DB_PASSWORD}"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${script_path}" 2>> "${LOG_FILE}"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to apply ${script_name}."
        unset PGPASSWORD
        exit 1
    fi
    log_message "${script_name} applied successfully."
    unset PGPASSWORD
}

# --- Main Script Logic ---

log_message "Starting database initialization process..."

# Check if DB_PASSWORD and PG_ADMIN_PASSWORD are set
if [ -z "${DB_PASSWORD}" ]; then
    log_message "ERROR: DB_PASSWORD environment variable is not set. Please set it before running this script."
    exit 1
fi
if [ -z "${PG_ADMIN_PASSWORD}" ]; then
    log_message "ERROR: PG_ADMIN_PASSWORD environment variable is not set. Please set it before running this script."
    exit 1
fi

check_prerequisites
create_db_and_user
run_alembic_migrations # This will create tables, foreign keys, and the audit trigger function/trigger

# Apply additional indexes and stored procedures not managed by Alembic (if any, though Alembic handles most)
# For this project, Alembic handles schema, indexes, and initial triggers.
# The `schema.sql` and `indexes.sql` are primarily for documentation/manual setup.
# `stored_procedures.sql` contains functions that might be added/modified outside of core schema migrations.
# `data_validation.sql` might contain additional triggers/functions.

# Re-applying these after Alembic is generally safe if they are idempotent (CREATE OR REPLACE).
# However, for a strict Alembic workflow, these should be part of Alembic migrations.
# For this exercise, we'll apply them separately to demonstrate their existence as distinct files.
apply_sql_script "${STORED_PROCEDURES_FILE}"
apply_sql_script "${INDEXES_FILE}" # Alembic already creates indexes, but this ensures any additional ones are there.
apply_sql_script "./data_validation.sql" # Apply data validation rules (e.g., triggers)

apply_sql_script "${SEED_DATA_FILE}"

log_message "Database initialization completed successfully."
echo "Database '${DB_NAME}' is ready."
echo "Check '${LOG_FILE}' for details."