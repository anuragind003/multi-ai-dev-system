#!/bin/bash

# This script performs a PostgreSQL database backup.
# It assumes PostgreSQL is running in a Docker container named 'db'
# and that pg_dump is available.

# Configuration
DB_CONTAINER_NAME="fastapi-monolith-db-1" # Or whatever your DB container is named in docker-compose
DB_USER="user"
DB_NAME="mydatabase"
BACKUP_DIR="/var/backups/postgresql" # Directory on the host where backups will be stored
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7 # Number of days to keep backups

echo "Starting PostgreSQL database backup for ${DB_NAME}..."

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform the backup using pg_dump from within the Docker container
# -Fc for custom format (recommended for pg_restore)
# -Z 9 for maximum compression
docker exec "${DB_CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc -Z 9 > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "Backup successful: ${BACKUP_FILE}"
else
    echo "Backup failed!"
    exit 1
fi

# Clean up old backups
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

if [ $? -eq 0 ]; then
    echo "Old backups cleaned up."
else
    echo "Failed to clean up old backups."
fi

echo "Backup process completed."