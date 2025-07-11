#!/bin/bash
# backup_restore.sh
# Script for performing PostgreSQL database backup and restore operations.

# --- Configuration ---
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="vkyc_db"
DB_USER="vkyc_user"
BACKUP_DIR="./backups" # Directory to store backups
DATE_FORMAT=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE_FORMAT}.sql"
LOG_FILE="./logs/backup_restore.log"

# Ensure log directory exists
mkdir -p ./logs

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# --- Functions ---

log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

perform_backup() {
    log_message "Starting database backup for '${DB_NAME}'..."
    log_message "Backup file: ${BACKUP_FILE}"

    # Use pg_dump to create a plain-text SQL dump
    # -h: host, -p: port, -U: user, -d: database, -F p: plain-text format
    # -v: verbose output, -Fc: custom format (binary) for larger databases is often better
    # For this example, plain-text is used for readability.
    PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -F p > "${BACKUP_FILE}" 2>> "${LOG_FILE}"

    if [ $? -eq 0 ]; then
        log_message "Database backup completed successfully."
        log_message "Backup size: $(du -h "${BACKUP_FILE}" | awk '{print $1}')"
    else
        log_message "ERROR: Database backup failed."
        rm -f "${BACKUP_FILE}" # Clean up failed backup file
        exit 1
    fi
}

perform_restore() {
    local restore_file="$1"
    local target_db_name="$2"

    if [ -z "$restore_file" ]; then
        log_message "ERROR: No backup file specified for restore."
        log_message "Usage: $0 restore <path_to_backup_file> [target_database_name]"
        exit 1
    fi

    if [ ! -f "$restore_file" ]; then
        log_message "ERROR: Backup file not found: ${restore_file}"
        exit 1
    fi

    if [ -z "$target_db_name" ]; then
        target_db_name="${DB_NAME}_restored" # Default target DB name
        log_message "No target database name specified. Restoring to a new database: '${target_db_name}'."
    else
        log_message "Restoring to database: '${target_db_name}'."
    fi

    log_message "Starting database restore from '${restore_file}' to '${target_db_name}'..."

    # Drop and recreate the target database to ensure a clean restore
    # Connect as postgres superuser to manage databases
    log_message "Attempting to drop and recreate database '${target_db_name}'..."
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${target_db_name}\";" 2>> "${LOG_FILE}"
    if [ $? -ne 0 ]; then
        log_message "WARNING: Could not drop database '${target_db_name}'. It might not exist or there are active connections. Attempting to create anyway."
    fi
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${target_db_name}\" OWNER \"${DB_USER}\";" 2>> "${LOG_FILE}"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to create database '${target_db_name}'. Aborting restore."
        exit 1
    fi
    log_message "Database '${target_db_name}' created successfully."

    # Restore the database from the backup file
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${target_db_name}" -f "${restore_file}" 2>> "${LOG_FILE}"

    if [ $? -eq 0 ]; then
        log_message "Database restore completed successfully to '${target_db_name}'."
    else
        log_message "ERROR: Database restore failed."
        exit 1
    fi
}

# --- Main Script Logic ---

# Read DB_PASSWORD securely (e.g., from environment variable or prompt)
# For production, avoid hardcoding passwords. Use environment variables or a secrets manager.
# Example: export DB_PASSWORD="your_strong_password_here" before running the script.
if [ -z "${DB_PASSWORD}" ]; then
    echo "Please set the DB_PASSWORD environment variable or enter it now:"
    read -s DB_PASSWORD
    export DB_PASSWORD # Export for pg_dump/psql
fi

case "$1" in
    backup)
        perform_backup
        ;;
    restore)
        perform_restore "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {backup|restore} [backup_file_path] [target_database_name]"
        echo "  backup: Creates a new database backup."
        echo "  restore: Restores a database from a specified backup file."
        echo "           [backup_file_path] is required for restore."
        echo "           [target_database_name] is optional; defaults to '${DB_NAME}_restored'."
        exit 1
        ;;
esac

exit 0