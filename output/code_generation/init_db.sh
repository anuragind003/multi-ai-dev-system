#!/bin/bash
# init_db.sh
# Comprehensive script to initialize the PostgreSQL database for the VKYC portal.
# This script creates the database, applies schema, runs migrations,
# sets up stored procedures, data validation, indexes, and seeds initial data.

# --- Configuration ---
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="vkyc_db"
DB_USER="vkyc_user"
DB_PASSWORD=$(grep -A 1 "\[database\]" database_config.ini | grep "password" | cut -d'=' -f2 | tr -d ' ')
ADMIN_USER="postgres" # Default PostgreSQL admin user for initial setup

# Paths to SQL and Python scripts
SCHEMA_SQL="schema.sql"
STORED_PROCEDURES_SQL="stored_procedures.sql"
DATA_VALIDATION_SQL="data_validation.sql"
INDEXES_SQL="indexes.sql"
SEED_DATA_SQL="seed_data.sql"
ALEMBIC_CONFIG_DIR="alembic" # Directory containing alembic.ini and env.py

# --- Helper Functions ---
log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
}

execute_sql_file() {
    local FILE_PATH="$1"
    log_message "Executing SQL file: $FILE_PATH"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$FILE_PATH"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to execute $FILE_PATH"
        exit 1
    fi
}

# --- Main Initialization Steps ---

log_message "Starting VKYC Database Initialization..."

# 1. Create Database User (if not exists)
log_message "Creating database user '$DB_USER' if it does not exist..."
# Connect as admin user to create the new user
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d postgres -c "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'User % created.', '$DB_USER';
    ELSE
        RAISE NOTICE 'User % already exists.', '$DB_USER';
    END IF;
END
\$\$;"
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to create database user '$DB_USER'."
    exit 1
fi

# 2. Create Database (if not exists) and Grant Privileges
log_message "Creating database '$DB_NAME' if it does not exist..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d postgres -c "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') THEN
        CREATE DATABASE $DB_NAME OWNER $DB_USER;
        RAISE NOTICE 'Database % created.', '$DB_NAME';
    ELSE
        RAISE NOTICE 'Database % already exists.', '$DB_NAME';
    END IF;
END
\$\$;"
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to create database '$DB_NAME'."
    exit 1
fi

# Grant all privileges on the database to the user
log_message "Granting all privileges on database '$DB_NAME' to user '$DB_USER'..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to grant privileges on database '$DB_NAME'."
    exit 1
fi

# 3. Enable UUID extension (if not already enabled)
log_message "Enabling 'pgcrypto' extension for gen_random_uuid()..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
if [ $? -ne 0 ]; then
    log_message "WARNING: Failed to enable 'pgcrypto' extension. UUID generation might rely on PostgreSQL 13+ built-in gen_random_uuid()."
fi

# 4. Run Alembic Migrations
log_message "Running Alembic migrations..."
# Ensure alembic.ini and env.py are correctly configured for the database
# We need to set PGPASSWORD for alembic to connect
export PGPASSWORD="$DB_PASSWORD"
cd "$ALEMBIC_CONFIG_DIR" || { log_message "ERROR: Alembic directory '$ALEMBIC_CONFIG_DIR' not found."; exit 1; }
alembic upgrade head
ALEMBIC_STATUS=$?
cd - > /dev/null # Go back to original directory
unset PGPASSWORD # Unset password for security

if [ $ALEMBIC_STATUS -ne 0 ]; then
    log_message "ERROR: Alembic migrations failed."
    exit 1
fi
log_message "Alembic migrations completed successfully."

# 5. Apply Stored Procedures/Functions
execute_sql_file "$STORED_PROCEDURES_SQL"

# 6. Apply Data Validation Rules (CHECK constraints)
execute_sql_file "$DATA_VALIDATION_SQL"

# 7. Apply Indexes
execute_sql_file "$INDEXES_SQL"

# 8. Seed Initial Data
execute_sql_file "$SEED_DATA_SQL"

log_message "Database initialization completed successfully for '$DB_NAME'."
log_message "You can now connect to the database using: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"