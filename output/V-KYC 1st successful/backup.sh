#!/bin/bash
# backup.sh
# Script to perform a full PostgreSQL database backup using pg_dump.

# --- Configuration ---
# Load database configuration from database.ini
CONFIG_FILE="database.ini"
DB_HOST=$(grep -E '^host\s*=' "$CONFIG_FILE" | sed 's/host\s*=\s*//')
DB_PORT=$(grep -E '^port\s*=' "$CONFIG_FILE" | sed 's/port\s*=\s*//')
DB_NAME=$(grep -E '^database\s*=' "$CONFIG_FILE" | sed 's/database\s*=\s*//')
DB_USER=$(grep -E '^user\s*=' "$CONFIG_FILE" | sed 's/user\s*=\s*//')
DB_PASSWORD=$(grep -E '^password\s*=' "$CONFIG_FILE" | sed 's/password\s*=\s*//')

# Backup directory (ensure this directory exists and has proper permissions)
BACKUP_DIR="./backups"
# Timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
# Backup file name
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
# Log file for backup operations
LOG_FILE="${BACKUP_DIR}/backup.log"

# --- Pre-checks ---
# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null
then
    echo "Error: pg_dump command not found. Please ensure PostgreSQL client tools are installed and in your PATH." | tee -a "$LOG_FILE"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# --- Backup Process ---
echo "Starting database backup for '$DB_NAME' at $(date)" | tee -a "$LOG_FILE"
echo "Backup file: $BACKUP_FILE" | tee -a "$LOG_FILE"

# Set PGPASSWORD environment variable for non-interactive password input
export PGPASSWORD="$DB_PASSWORD"

# Perform the backup
# -h: host
# -p: port
# -U: user
# -d: database name
# -F p: plain-text format (for easy viewing/editing, use -F c for custom/compressed)
# -v: verbose mode
# -f: output file
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F p -v -f "$BACKUP_FILE" 2>> "$LOG_FILE"

# Check the exit status of pg_dump
if [ $? -eq 0 ]; then
    echo "Backup completed successfully!" | tee -a "$LOG_FILE"
    echo "Backup size: $(du -h "$BACKUP_FILE" | awk '{print $1}')" | tee -a "$LOG_FILE"
else
    echo "Error: Database backup failed!" | tee -a "$LOG_FILE"
    # Optionally, add error notification logic here (e.g., email, Slack)
fi

# Unset PGPASSWORD for security
unset PGPASSWORD

echo "Backup script finished at $(date)" | tee -a "$LOG_FILE"
echo "---------------------------------------------------" | tee -a "$LOG_FILE"

# --- Retention Policy (Optional) ---
# Keep only the last 7 days of backups
# find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.sql" -mtime +7 -delete
# echo "Old backups (older than 7 days) cleaned up." | tee -a "$LOG_FILE"