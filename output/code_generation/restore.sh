#!/bin/bash
# restore.sh
# Script to restore a PostgreSQL database from a backup file.

# --- Configuration ---
# Load database configuration from database.ini
CONFIG_FILE="database.ini"
DB_HOST=$(grep -E '^host\s*=' "$CONFIG_FILE" | sed 's/host\s*=\s*//')
DB_PORT=$(grep -E '^port\s*=' "$CONFIG_FILE" | sed 's/port\s*=\s*//')
DB_NAME=$(grep -E '^database\s*=' "$CONFIG_FILE" | sed 's/database\s*=\s*//')
DB_USER=$(grep -E '^user\s*=' "$CONFIG_FILE" | sed 's/user\s*=\s*//')
DB_PASSWORD=$(grep -E '^password\s*=' "$CONFIG_FILE" | sed 's/password\s*=\s*//')

# Backup directory
BACKUP_DIR="./backups"
# Log file for restore operations
LOG_FILE="${BACKUP_DIR}/restore.log"

# --- Usage ---
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file_path>" | tee -a "$LOG_FILE"
    echo "Example: $0 ./backups/vkyc_db_20231027_100000.sql" | tee -a "$LOG_FILE"
    echo "Available backups:" | tee -a "$LOG_FILE"
    ls -lh "$BACKUP_DIR"/*.sql 2>/dev/null || echo "No backup files found in $BACKUP_DIR." | tee -a "$LOG_FILE"
    exit 1
fi

BACKUP_FILE="$1"

# --- Pre-checks ---
# Check if pg_restore or psql is available
if ! command -v psql &> /dev/null
then
    echo "Error: psql command not found. Please ensure PostgreSQL client tools are installed and in your PATH." | tee -a "$LOG_FILE"
    exit 1
fi

# Check if the backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found." | tee -a "$LOG_FILE"
    exit 1
fi

# --- Restore Process ---
echo "Starting database restore for '$DB_NAME' from '$BACKUP_FILE' at $(date)" | tee -a "$LOG_FILE"

# Set PGPASSWORD environment variable for non-interactive password input
export PGPASSWORD="$DB_PASSWORD"

# Drop existing database (DANGER: This will delete all current data!)
echo "WARNING: This will drop and recreate the database '$DB_NAME'. All existing data will be lost." | tee -a "$LOG_FILE"
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled by user." | tee -a "$LOG_FILE"
    unset PGPASSWORD
    exit 0
fi

echo "Dropping database '$DB_NAME'..." | tee -a "$LOG_FILE"
# Connect to 'postgres' database to drop the target database
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>> "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to drop database '$DB_NAME'. It might be in use. Please ensure no active connections." | tee -a "$LOG_FILE"
    unset PGPASSWORD
    exit 1
fi

echo "Creating database '$DB_NAME'..." | tee -a "$LOG_FILE"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" 2>> "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create database '$DB_NAME'." | tee -a "$LOG_FILE"
    unset PGPASSWORD
    exit 1
fi

echo "Restoring database from '$BACKUP_FILE'..." | tee -a "$LOG_FILE"
# Restore the database using psql (for plain-text backups)
# For custom/compressed backups (-F c), use pg_restore instead:
# pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v "$BACKUP_FILE" 2>> "$LOG_FILE"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE" 2>> "$LOG_FILE"

# Check the exit status of psql
if [ $? -eq 0 ]; then
    echo "Restore completed successfully!" | tee -a "$LOG_FILE"
else
    echo "Error: Database restore failed!" | tee -a "$LOG_FILE"
    # Optionally, add error notification logic here
fi

# Unset PGPASSWORD for security
unset PGPASSWORD

echo "Restore script finished at $(date)" | tee -a "$LOG_FILE"
echo "---------------------------------------------------" | tee -a "$LOG_FILE"