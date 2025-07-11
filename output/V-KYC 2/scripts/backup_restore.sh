#!/bin/bash

# This script provides basic functions for backing up and restoring a PostgreSQL database.
# It assumes:
# - PostgreSQL client tools (pg_dump, pg_restore) are available.
# - Database credentials are provided via environment variables or directly in the script (less secure).
# - Backup files are stored locally or transferred to a remote storage.

# --- Configuration ---
DB_HOST=${DATABASE_HOST:-localhost}
DB_PORT=${DATABASE_PORT:-5432}
DB_USER=${DATABASE_USER:-prod_user}
DB_NAME=${DATABASE_NAME:-prod_db}
BACKUP_DIR="/var/backups/fastapi_db" # Local directory for backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/fastapi_db_backup_${TIMESTAMP}.sqlc" # .sqlc for custom format

# --- Functions ---
log_info() {
  echo "[INFO] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
  exit 1
}

create_backup_dir() {
  if [ ! -d "$BACKUP_DIR" ]; then
    log_info "Creating backup directory: $BACKUP_DIR"
    sudo mkdir -p "$BACKUP_DIR" || log_error "Failed to create backup directory."
    sudo chown -R $(whoami):$(whoami) "$BACKUP_DIR" # Adjust ownership as needed
  fi
}

backup_database() {
  log_info "Starting database backup for ${DB_NAME} on ${DB_HOST}..."
  create_backup_dir

  # Use PGPASSWORD environment variable for non-interactive password entry
  # IMPORTANT: In production, use a more secure method like .pgpass file or vault.
  PGPASSWORD="${DATABASE_PASSWORD}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" -f "$BACKUP_FILE"
  if [ $? -eq 0 ]; then
    log_info "Database backup successful: $BACKUP_FILE"
    # Optional: Upload to S3 or other cloud storage
    # aws s3 cp "$BACKUP_FILE" "s3://your-backup-bucket/fastapi-db/"
  else
    log_error "Database backup failed."
  fi
}

restore_database() {
  local restore_file="$1"
  if [ -z "$restore_file" ]; then
    log_error "Usage: restore_database <path_to_backup_file>"
  fi

  if [ ! -f "$restore_file" ]; then
    log_error "Backup file not found: $restore_file"
  fi

  log_info "Starting database restore for ${DB_NAME} on ${DB_HOST} from ${restore_file}..."

  # Drop existing database and create a new one (DANGER: This will delete all current data!)
  # In a real scenario, you might restore to a new DB and then switch, or use a more granular restore.
  log_info "Dropping and recreating database ${DB_NAME}..."
  PGPASSWORD="${DATABASE_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME};" || log_error "Failed to drop database."
  PGPASSWORD="${DATABASE_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || log_error "Failed to create database."

  # Restore from backup
  PGPASSWORD="${DATABASE_PASSWORD}" pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$restore_file"
  if [ $? -eq 0 ]; then
    log_info "Database restore successful."
  else
    log_error "Database restore failed."
  fi
}

# --- Script Execution ---
case "$1" in
  backup)
    backup_database
    ;;
  restore)
    restore_database "$2"
    ;;
  *)
    echo "Usage: $0 {backup|restore <path_to_backup_file>}"
    exit 1
    ;;
esac