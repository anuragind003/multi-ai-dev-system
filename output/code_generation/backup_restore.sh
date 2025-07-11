#!/bin/bash
# backup_restore.sh
# Shell scripts for performing PostgreSQL database backup and restore operations.

# --- Configuration ---
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="vkyc_db"
DB_USER="vkyc_user"
BACKUP_DIR="./backups" # Directory to store backups
DATE_FORMAT=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE_FORMAT}.sql"
LOG_FILE="${BACKUP_DIR}/backup_restore.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR" || { echo "Error: Could not create backup directory $BACKUP_DIR"; exit 1; }

# Function to log messages
log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --- Backup Function ---
backup_database() {
    log_message "Starting database backup for '$DB_NAME'..."
    log_message "Backup file: $BACKUP_FILE"

    # Use PGPASSWORD environment variable for non-interactive password entry
    # It's recommended to use .pgpass file or other secure methods in production.
    export PGPASSWORD=$(grep -A 1 "\[database\]" database_config.ini | grep "password" | cut -d'=' -f2 | tr -d ' ')

    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F p -v -f "$BACKUP_FILE" "$DB_NAME"
    BACKUP_STATUS=$?

    unset PGPASSWORD # Unset password for security

    if [ $BACKUP_STATUS -eq 0 ]; then
        log_message "Database backup completed successfully to $BACKUP_FILE"
        # Optional: Compress the backup file
        gzip "$BACKUP_FILE"
        log_message "Backup file compressed to ${BACKUP_FILE}.gz"
    else
        log_message "ERROR: Database backup failed with exit code $BACKUP_STATUS"
        rm -f "$BACKUP_FILE" # Clean up incomplete backup file
        exit 1
    fi
}

# --- Restore Function ---
restore_database() {
    local RESTORE_FILE="$1"

    if [ -z "$RESTORE_FILE" ]; then
        log_message "ERROR: No restore file specified. Usage: $0 restore <path_to_backup_file>"
        exit 1
    fi

    if [ ! -f "$RESTORE_FILE" ]; then
        log_message "ERROR: Restore file '$RESTORE_FILE' not found."
        exit 1
    fi

    log_message "Starting database restore for '$DB_NAME' from '$RESTORE_FILE'..."

    # Check if the file is gzipped and decompress if necessary
    if [[ "$RESTORE_FILE" == *.gz ]]; then
        log_message "Decompressing $RESTORE_FILE..."
        gunzip -c "$RESTORE_FILE" > "${RESTORE_FILE%.gz}"
        RESTORE_FILE="${RESTORE_FILE%.gz}"
        DECOMPRESSED=true
    fi

    # Use PGPASSWORD environment variable
    export PGPASSWORD=$(grep -A 1 "\[database\]" database_config.ini | grep "password" | cut -d'=' -f2 | tr -d ' ')

    # Drop existing database and recreate it to ensure a clean restore
    log_message "Dropping existing database '$DB_NAME'..."
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || { log_message "WARNING: Could not drop database '$DB_NAME'. It might not exist or connections are active. Attempting to create anyway."; }

    log_message "Creating new database '$DB_NAME'..."
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || { log_message "ERROR: Could not create database '$DB_NAME'. Check permissions or if it already exists."; exit 1; }

    log_message "Restoring data into '$DB_NAME'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$RESTORE_FILE"
    RESTORE_STATUS=$?

    unset PGPASSWORD # Unset password for security

    if [ $RESTORE_STATUS -eq 0 ]; then
        log_message "Database restore completed successfully from $RESTORE_FILE"
    else
        log_message "ERROR: Database restore failed with exit code $RESTORE_STATUS"
        exit 1
    fi

    # Clean up decompressed file if it was created
    if [ "$DECOMPRESSED" = true ]; then
        rm -f "$RESTORE_FILE"
        log_message "Cleaned up decompressed file: $RESTORE_FILE"
    fi
}

# --- Main Script Logic ---
case "$1" in
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    *)
        echo "Usage: $0 {backup|restore} [backup_file_path_for_restore]"
        echo "Example: $0 backup"
        echo "Example: $0 restore ./backups/vkyc_db_20231027_100000.sql.gz"
        exit 1
        ;;
esac