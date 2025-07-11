#!/bin/bash
# backup_restore_scripts.sh
# Provides scripts for database backup and restore.

# Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"  # Use a dedicated backup user in production.
DB_PASSWORD="admin_password" # Replace with the actual password.
BACKUP_DIR="/var/backups/postgres"  # Directory for backups.  Ensure this exists and is writeable.
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql.gz"

# Function to handle errors
error_exit() {
  echo "ERROR: $1"
  exit 1
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR" || error_exit "Failed to create backup directory."

# Backup script
backup_db() {
  echo "Starting database backup..."
  pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -W -d "$DB_NAME" --file="$BACKUP_FILE" --format=c || error_exit "Failed to create backup."
  echo "Backup completed successfully: $BACKUP_FILE"
}

# Restore script
restore_db() {
  echo "Starting database restore..."
  if [ ! -f "$1" ]; then
    error_exit "Backup file not found: $1"
  fi

  pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -W -d "$DB_NAME" "$1" || error_exit "Failed to restore database."
  echo "Database restored successfully from: $1"
}

# Main script logic
case "$1" in
  backup)
    backup_db
    ;;
  restore)
    restore_db "$2"
    ;;
  *)
    echo "Usage: $0 {backup|restore} [backup_file]"
    exit 1
    ;;
esac

exit 0