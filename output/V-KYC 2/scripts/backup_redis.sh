#!/bin/bash

# This script performs a Redis backup by triggering BGSAVE and copying the RDB file.
# It assumes Redis is running and accessible from where this script is executed.

# Configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}" # Empty if no password
REDIS_CLI_PATH="${REDIS_CLI_PATH:-redis-cli}" # Path to redis-cli executable
REDIS_DATA_DIR="/var/lib/redis" # Default Redis data directory inside container/host
REDIS_RDB_FILE="dump.rdb" # Default RDB filename

BACKUP_DESTINATION="$1" # First argument is the backup destination path

# Check if backup destination is provided
if [ -z "$BACKUP_DESTINATION" ]; then
  echo "Usage: $0 <backup_destination_path>"
  echo "Example: $0 /mnt/backups/redis"
  echo "Example: $0 s3://my-redis-backups/fastapi-app"
  exit 1
fi

# Add Redis password to redis-cli command if set
REDIS_AUTH_CMD=""
if [ -n "$REDIS_PASSWORD" ]; then
  REDIS_AUTH_CMD="-a $REDIS_PASSWORD"
fi

echo "--- Starting Redis Backup ---"
echo "Redis Host: $REDIS_HOST"
echo "Redis Port: $REDIS_PORT"
echo "Backup Destination: $BACKUP_DESTINATION"

# 1. Trigger BGSAVE to create a new RDB snapshot
echo "Triggering Redis BGSAVE..."
if ! $REDIS_CLI_PATH -h "$REDIS_HOST" -p "$REDIS_PORT" $REDIS_AUTH_CMD BGSAVE; then
  echo "Error: Failed to trigger BGSAVE. Check Redis connection and authentication."
  exit 1
fi
echo "BGSAVE command sent. Waiting for save to complete (check Redis logs for progress)."

# Give Redis some time to complete the save operation
# In a production environment, you might want to poll INFO persistence for rdb_last_save_time
# or check Redis logs for "DB saved on disk" message.
sleep 10 # Adjust based on your data size

# 2. Determine the source of the RDB file
# If Redis is running in Docker, we need to copy from the container.
# If Redis is running directly on the host, we can copy from REDIS_DATA_DIR.

# Check if Redis is a Docker container
REDIS_CONTAINER_ID=$(docker ps -q --filter "name=redis" --filter "ancestor=redis:7-alpine")

if [ -n "$REDIS_CONTAINER_ID" ]; then
  echo "Redis is running in Docker container: $REDIS_CONTAINER_ID"
  SOURCE_PATH="$REDIS_CONTAINER_ID:$REDIS_DATA_DIR/$REDIS_RDB_FILE"
  COPY_CMD="docker cp"
else
  echo "Redis is assumed to be running on host or accessible via mounted volume."
  SOURCE_PATH="$REDIS_DATA_DIR/$REDIS_RDB_FILE"
  COPY_CMD="cp"
fi

# 3. Copy the RDB file to the backup destination
BACKUP_FILENAME="dump_$(date +%Y%m%d_%H%M%S).rdb"

if [[ "$BACKUP_DESTINATION" == s3://* ]]; then
  # AWS S3 backup
  echo "Copying $SOURCE_PATH to S3: $BACKUP_DESTINATION/$BACKUP_FILENAME"
  if [ -n "$REDIS_CONTAINER_ID" ]; then
    # Copy from container to a temporary host path, then upload to S3
    TEMP_HOST_PATH="/tmp/$REDIS_RDB_FILE"
    if ! docker cp "$SOURCE_PATH" "$TEMP_HOST_PATH"; then
      echo "Error: Failed to copy RDB from Docker container to temporary host path."
      exit 1
    fi
    if ! aws s3 cp "$TEMP_HOST_PATH" "$BACKUP_DESTINATION/$BACKUP_FILENAME"; then
      echo "Error: Failed to upload RDB to S3."
      rm -f "$TEMP_HOST_PATH" # Clean up temp file
      exit 1
    fi
    rm -f "$TEMP_HOST_PATH" # Clean up temp file
  else
    # Copy directly from host to S3
    if ! aws s3 cp "$SOURCE_PATH" "$BACKUP_DESTINATION/$BACKUP_FILENAME"; then
      echo "Error: Failed to upload RDB to S3."
      exit 1
    fi
  fi
else
  # Local/NFS backup
  echo "Copying $SOURCE_PATH to local path: $BACKUP_DESTINATION/$BACKUP_FILENAME"
  mkdir -p "$BACKUP_DESTINATION" # Ensure destination directory exists
  if [ -n "$REDIS_CONTAINER_ID" ]; then
    if ! docker cp "$SOURCE_PATH" "$BACKUP_DESTINATION/$BACKUP_FILENAME"; then
      echo "Error: Failed to copy RDB from Docker container to local path."
      exit 1
    fi
  else
    if ! cp "$SOURCE_PATH" "$BACKUP_DESTINATION/$BACKUP_FILENAME"; then
      echo "Error: Failed to copy RDB to local path."
      exit 1
    fi
  fi
fi

echo "--- Redis Backup Completed Successfully ---"
echo "Backup file: $BACKUP_DESTINATION/$BACKUP_FILENAME"

# Optional: Verify backup file integrity (e.g., check file size, or use redis-check-rdb)
# For redis-check-rdb, you'd need to have it installed or run it in a Redis container.
# Example: docker run --rm -v /path/to/backup:/data redis:7-alpine redis-check-rdb /data/dump_*.rdb