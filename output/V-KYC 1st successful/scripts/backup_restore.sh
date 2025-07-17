#!/bin/bash
# scripts/backup_restore.sh
# This script provides functions for backing up and restoring the PostgreSQL database.
# It uses pg_dump for backups and pg_restore for restoration.

# --- Configuration ---
# Load database credentials from config/database.ini
CONFIG_FILE="config/database.ini"
DB_HOST=$(grep -E '^host\s*=' "$CONFIG_FILE" | sed -E 's/host\s*=\s*(.*)/\1/')
DB_PORT=$(grep -E '^port\s*=' "$CONFIG_FILE" | sed -E 's/port\s*=\s*(.*)/\1/')
DB_NAME=$(grep -E '^database\s*=' "$CONFIG_FILE" | sed -E 's/database\s*=\s*(.*)/\1/')
DB_USER=$(grep -E '^user\s*=' "$CONFIG_FILE" | sed -E 's/user\s*=\s*(.*)/\1/')
DB_PASSWORD=$(grep -E '^password\s*=' "$CONFIG_FILE" | sed -E 's/password\s*=\s*(.*)/\1/')

# Set environment variables for pg_dump/pg_restore
export PGPASSWORD=$DB_PASSWORD

BACKUP_DIR="db_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump"
LOG_FILE="$BACKUP_DIR/backup_restore.log"

# --- Functions ---

log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_message "Created backup directory: $BACKUP_DIR"
    fi
}

backup_database() {
    create_backup_dir
    log_message "Starting database backup for '$DB_NAME' to '$BACKUP_FILE'..."
    
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE" 2>> "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log_message "Database backup successful: '$BACKUP_FILE'"
        # Optional: Compress the backup file
        gzip "$BACKUP_FILE"
        BACKUP_FILE="$BACKUP_FILE.gz"
        log_message "Backup compressed to '$BACKUP_FILE'"
    else
        log_message "ERROR: Database backup failed for '$DB_NAME'."
        return 1
    fi
    return 0
}

restore_database() {
    local restore_file="$1"
    local target_db_name="$2"

    if [ -z "$restore_file" ]; then
        log_message "ERROR: No backup file specified for restoration."
        echo "Usage: $0 restore <backup_file> [target_database_name]"
        return 1
    fi

    if [ ! -f "$restore_file" ]; then
        log_message "ERROR: Backup file not found: '$restore_file'"
        return 1
    fi

    if [ -z "$target_db_name" ]; then
        target_db_name="$DB_NAME"
        log_message "No target database name specified. Restoring to default database: '$target_db_name'"
    else
        log_message "Restoring '$restore_file' to database '$target_db_name'."
    fi

    log_message "Attempting to drop and recreate database '$target_db_name'..."
    # Connect to postgres database to drop/create target_db_name
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$target_db_name\";" 2>> "$LOG_FILE"
    if [ $? -ne 0 ]; then
        log_message "WARNING: Could not drop database '$target_db_name'. It might not exist or there are active connections."
        log_message "Please ensure no active connections to '$target_db_name' before attempting restore."
        # Attempt to terminate all connections to the database
        log_message "Attempting to terminate all active connections to '$target_db_name'..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$target_db_name' AND pid <> pg_backend_pid();" 2>> "$LOG_FILE"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$target_db_name\";" 2>> "$LOG_FILE"
        if [ $? -ne 0 ]; then
            log_message "ERROR: Failed to drop database '$target_db_name' even after terminating connections. Aborting restore."
            return 1
        fi
    fi

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$target_db_name\" OWNER \"$DB_USER\";" 2>> "$LOG_FILE"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to create database '$target_db_name'. Aborting restore."
        return 1
    fi
    log_message "Database '$target_db_name' recreated successfully."

    log_message "Starting database restoration from '$restore_file' to '$target_db_name'..."
    
    # Decompress if it's a gzipped file
    local temp_restore_file="$restore_file"
    if [[ "$restore_file" == *.gz ]]; then
        log_message "Decompressing backup file..."
        gunzip -c "$restore_file" > "${restore_file%.gz}" 2>> "$LOG_FILE"
        if [ $? -ne 0 ]; then
            log_message "ERROR: Failed to decompress backup file. Aborting restore."
            return 1
        fi
        temp_restore_file="${restore_file%.gz}"
    fi

    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$target_db_name" "$temp_restore_file" 2>> "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log_message "Database restoration successful to '$target_db_name'."
    else
        log_message "ERROR: Database restoration failed to '$target_db_name'."
        return 1
    fi

    # Clean up decompressed file if it was gzipped
    if [[ "$restore_file" == *.gz ]]; then
        rm -f "$temp_restore_file"
        log_message "Cleaned up temporary decompressed file."
    fi
    return 0
}

# --- Main Script Logic ---
case "$1" in
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {backup|restore}"
        echo "  backup: Creates a new backup of the database."
        echo "  restore <backup_file> [target_database_name]: Restores the database from a specified backup file."
        echo "    If target_database_name is not provided, it defaults to the configured DB_NAME."
        exit 1
        ;;
esac

# Unset PGPASSWORD for security
unset PGPASSWORD