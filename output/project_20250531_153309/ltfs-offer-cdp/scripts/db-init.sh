#!/bin/bash
#
# db-init.sh
#
# Script for initial PostgreSQL database setup, schema creation, and seeding with test data
# for the LTFS Offer CDP project.
#
# This script automates the process of:
# 1. Checking for necessary dependencies (psql client).
# 2. Waiting for the PostgreSQL database server to become available.
# 3. Creating the target database if it does not already exist.
# 4. Executing SQL scripts for schema creation and data seeding.
#
# Usage:
#   To run with default settings:
#     ./db-init.sh
#
#   To run with custom settings (e.g., for a remote DB or different credentials):
#     DB_HOST=my_db_host DB_PORT=5432 DB_USER=myuser DB_PASSWORD=mypassword DB_NAME=my_cdp_db ./db-init.sh
#
# Environment Variables (can be set before running the script):
#   DB_HOST     - PostgreSQL host (default: localhost)
#   DB_PORT     - PostgreSQL port (default: 5432)
#   DB_USER     - PostgreSQL user (default: postgres)
#   DB_PASSWORD - PostgreSQL password (default: password)
#   DB_NAME     - Database name to create/initialize (default: ltfs_offer_cdp_db)
#   WAIT_TIMEOUT - Timeout in seconds for waiting for DB readiness (default: 60)

# --- Configuration ---

# Set default values for database connection parameters.
# These can be overridden by setting environment variables before running the script.
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-password}"
DB_NAME="${DB_NAME:-ltfs_offer_cdp_db}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-60}" # Timeout in seconds for waiting for the database to be ready

# Determine the directory where this script is located.
# This allows SQL files to be referenced relative to the script's location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
SQL_DIR="${SCRIPT_DIR}/sql" # Assumes SQL files are in a 'sql' subdirectory relative to the script

# Define paths to the SQL schema and data files.
# These files are expected to contain DDL (Data Definition Language) for schema
# and DML (Data Manipulation Language) for initial data.
SQL_SCHEMA_FILE="${SQL_DIR}/schema.sql"
SQL_DATA_FILE="${SQL_DIR}/data.sql"

# --- Error Handling and Logging ---

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error when substituting.
# The return value of a pipeline is the status of the last command to exit with a non-zero status,
# or zero if all commands in the pipeline exit successfully.
set -euo pipefail

# Function to log informational messages to standard output.
log_info() {
  echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $1"
}

# Function to log error messages to standard error and exit the script with a non-zero status.
log_error() {
  echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
  exit 1
}

# --- Helper Functions ---

# Checks if the 'psql' command-line client is installed and available in the PATH.
# 'psql' is required to interact with the PostgreSQL database.
check_dependencies() {
  log_info "Checking for psql client..."
  if ! command -v psql &>/dev/null; then
    log_error "psql command not found. Please install PostgreSQL client tools (e.g., 'postgresql-client')."
  fi
  log_info "psql client found."
}

# Waits for the PostgreSQL database server to become ready and accessible.
# It uses 'pg_isready' for a robust check, retrying until the database is up or a timeout is reached.
wait_for_db() {
  log_info "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} to be ready..."
  local start_time=$(date +%s)
  local current_time
  local elapsed_time

  # Set PGPASSWORD environment variable for psql to avoid password prompts.
  # This is a common practice for scripting but should be handled securely in production.
  export PGPASSWORD="${DB_PASSWORD}"

  while true; do
    # pg_isready checks the connection status of a PostgreSQL server.
    # -h: host, -p: port, -U: user, -q: quiet mode (no output).
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q; then
      log_info "PostgreSQL is ready."
      break
    fi

    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))

    if ((elapsed_time >= WAIT_TIMEOUT)); then
      log_error "Timeout (${WAIT_TIMEOUT}s) reached while waiting for PostgreSQL."
    fi

    log_info "PostgreSQL not yet ready. Waiting 5 seconds..."
    sleep 5
  done
  # Unset PGPASSWORD immediately after use for security best practices.
  unset PGPASSWORD
}

# Creates the target database if it does not already exist.
# It connects to the default 'postgres' database to perform the creation.
create_database_if_not_exists() {
  log_info "Attempting to create database '${DB_NAME}' if it does not exist..."
  export PGPASSWORD="${DB_PASSWORD}"

  # Check if the database already exists by querying pg_database.
  # -tAc: tuple only, no headers, single column, execute command.
  # Connects to 'postgres' database as it's a common default for administrative tasks.
  if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    log_info "Database '${DB_NAME}' already exists. Skipping creation."
  else
    log_info "Database '${DB_NAME}' does not exist. Creating..."
    # Execute the CREATE DATABASE command.
    if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME}"; then
      log_info "Database '${DB_NAME}' created successfully."
    else
      log_error "Failed to create database '${DB_NAME}'. Check PostgreSQL user permissions or server logs."
    fi
  fi
  unset PGPASSWORD
}

# Executes one or more SQL script files against the specified database.
# This function is used for both schema creation and data seeding.
run_sql_scripts() {
  local db_name="$1" # The database name to connect to
  shift              # Remove the first argument (db_name) from the list
  local sql_files=("$@") # Remaining arguments are the SQL file paths

  export PGPASSWORD="${DB_PASSWORD}"

  for sql_file in "${sql_files[@]}"; do
    if [[ ! -f "${sql_file}" ]]; then
      log_error "SQL file not found: ${sql_file}. Please ensure it exists in the 'sql' directory."
    fi
    log_info "Executing SQL script: ${sql_file} on database '${db_name}'..."
    # -f: execute commands from file.
    if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${db_name}" -f "${sql_file}"; then
      log_info "Successfully executed ${sql_file}."
    else
      log_error "Failed to execute ${sql_file}. Review the SQL file for errors or check database connection/permissions."
    fi
  done
  unset PGPASSWORD
}

# --- Main Execution Flow ---

# The main function orchestrates the entire database initialization process.
main() {
  log_info "Starting LTFS Offer CDP Database Initialization Script."

  # Step 1: Verify that the 'psql' client is installed.
  check_dependencies

  # Step 2: Wait for the PostgreSQL server to be available.
  wait_for_db

  # Step 3: Create the target database if it doesn't already exist.
  create_database_if_not_exists

  # Step 4: Run the schema creation SQL script.
  # This script should contain all CREATE TABLE, CREATE INDEX, etc., statements.
  run_sql_scripts "${DB_NAME}" "${SQL_SCHEMA_FILE}"

  # Step 5: Run the data seeding SQL script (optional).
  # This script can contain INSERT statements for initial or test data.
  # It's checked for existence before execution, allowing the script to run without it.
  if [[ -f "${SQL_DATA_FILE}" ]]; then
    run_sql_scripts "${DB_NAME}" "${SQL_DATA_FILE}"
  else
    log_info "No data seeding file found at ${SQL_DATA_FILE}. Skipping data seeding."
  fi

  log_info "LTFS Offer CDP Database Initialization Complete."
}

# Call the main function to start the script execution.
main "$@"