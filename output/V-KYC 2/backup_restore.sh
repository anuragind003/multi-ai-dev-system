#!/bin/bash
# backup_restore.sh
# Shell scripts for performing PostgreSQL database backup and restore operations.
# Uses pg_dump and pg_restore utilities.

# --- Configuration ---
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-vkyc_db}"
DB_USER="${DB_USER:-vkyc_user}"
# It's highly recommended to set PGPASSWORD environment variable or use .pgpass file
# for production environments instead of passing password directly on command line.
# export PGPASSWORD="vkyc_password"

BACKUP_DIR="${BACKUP_DIR:-./db_backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${DB_NAME}_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup_restore.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR" || { echo "Error: Could not create backup directory $BACKUP_DIR"; exit 1; }

# --- Logging Function ---
log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# --- Backup Function ---
backup_database() {
    log_message "Starting database backup for '$DB_NAME' to '$BACKUP_DIR/$BACKUP_FILE'..."
    log_message "Using DB_HOST: $DB_HOST, DB_PORT: $DB_PORT, DB_USER: $DB_USER"

    # pg_dump command:
    # -h: host
    # -p: port
    # -U: user
    # -Fc: custom format archive file (recommended for pg_restore)
    # -v: verbose mode
    # -f: output file
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc -v -f "$BACKUP_DIR/$BACKUP_FILE" "$DB_NAME"

    if [ $? -eq 0 ]; then
        log_message "Database backup successful: $BACKUP_DIR/$BACKUP_FILE"
        # Optional: Clean up old backups (e.g., keep last 7 days)
        # find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -mtime +7 -delete
        # log_message "Old backups cleaned up."
    else
        log_message "Database backup FAILED!"
        exit 1
    fi
}

# --- Restore Function ---
restore_database() {
    local restore_file="$1"
    if [ -z "$restore_file" ]; then
        log_message "Error: No backup file specified for restore."
        log_message "Usage: $0 restore <path_to_backup_file>"
        exit 1
    fi

    if [ ! -f "$restore_file" ]; then
        log_message "Error: Backup file '$restore_file' not found."
        exit 1
    fi

    log_message "Starting database restore for '$DB_NAME' from '$restore_file'..."
    log_message "WARNING: This will drop and recreate the database '$DB_NAME'. All existing data will be lost."
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_message "Restore cancelled by user."
        exit 0
    fi

    # Drop and recreate the database to ensure a clean slate
    log_message "Dropping existing database '$DB_NAME'..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" template1
    if [ $? -ne 0 ]; then
        log_message "Error: Failed to drop database '$DB_NAME'."
        exit 1
    fi

    log_message "Creating new database '$DB_NAME'..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" template1
    if [ $? -ne 0 ]; then
        log_message "Error: Failed to create database '$DB_NAME'."
        exit 1
    fi

    # pg_restore command:
    # -h: host
    # -p: port
    # -U: user
    # -d: database to restore into
    # -v: verbose mode
    PGPASSWORD="$DB_PASSWORD" pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v "$restore_file"

    if [ $? -eq 0 ]; then
        log_message "Database restore successful from '$restore_file'."
    else
        log_message "Database restore FAILED!"
        exit 1
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
        echo "  backup: Creates a new database backup."
        echo "  restore: Restores the database from a specified backup file."
        exit 1
        ;;
esac

exit 0