#!/bin/bash

# This script restores a PostgreSQL database from a backup file.
# It assumes PostgreSQL is running in a Docker container named 'db'
# and that pg_restore is available.

# Configuration
DB_CONTAINER_NAME="fastapi-monolith-db-1" # Or whatever your DB container is named in docker-compose
DB_USER="user"
DB_NAME="mydatabase"
BACKUP_DIR="/var/backups/postgresql" # Directory on the host where backups are stored

echo "Available backup files in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || { echo "No backup files found in ${BACKUP_DIR}. Exiting."; exit 1; }

read -p "Enter the full path to the backup file to restore (e.g., ${BACKUP_DIR}/mydatabase_YYYYMMDD_HHMMSS.sql.gz): " RESTORE_FILE

if [ -z "${RESTORE_FILE}" ]; then
    echo "No file specified. Exiting."
    exit 1
fi

if [ ! -f "${RESTORE_FILE}" ]; then
    echo "Error: Backup file not found at ${RESTORE_FILE}. Exiting."
    exit 1
fi

echo "Attempting to restore database ${DB_NAME} from ${RESTORE_FILE}..."

# Stop the application services that might be connected to the DB
echo "Stopping application services to ensure exclusive DB access..."
docker-compose -f docker-compose.prod.yml stop backend # Adjust if other services connect to DB

# Drop and recreate the database to ensure a clean slate
echo "Dropping and recreating database ${DB_NAME}..."
docker exec "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"

# Perform the restore using pg_restore
# -Fc format requires pg_restore, not psql
gunzip -c "${RESTORE_FILE}" | docker exec -i "${DB_CONTAINER_NAME}" pg_restore -U "${DB_USER}" -d "${DB_NAME}"

if [ $? -eq 0 ]; then
    echo "Database restore successful from ${RESTORE_FILE}."
else
    echo "Database restore failed!"
    # Recreate the database if restore failed to leave it in a usable state
    docker exec "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    docker exec "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"
    exit 1
fi

# Start the application services again
echo "Starting application services..."
docker-compose -f docker-compose.prod.yml start backend

echo "Restore process completed. Please verify your application data."