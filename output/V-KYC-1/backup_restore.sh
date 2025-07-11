#!/bin/bash

# backup_restore.sh
# Script for performing PostgreSQL database backup and restore operations.
# Uses pg_dump for backups and pg_restore for restores.

# --- Configuration ---
# Read database credentials from config/database.ini
CONFIG_FILE="config/database.ini"
DB_HOST=$(grep -E '^host=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_PORT=$(grep -E '^port=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_NAME=$(grep -E '^dbname=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_USER=$(grep -E '^user=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_PASSWORD=$(grep -E '^password=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')

# Backup directory
BACKUP_DIR="backups"
SCHEMA_ONLY_DIR="$BACKUP_DIR/schema_only"
DATA_ONLY_DIR="$BACKUP_DIR/data_only"

# Ensure backup directories exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$SCHEMA_ONLY_DIR"
mkdir -p "$DATA_ONLY_DIR"

# Set PGPASSWORD for non-interactive login (securely managed in production)
export PGPASSWORD="$DB_PASSWORD"

# --- Functions ---

# Function to perform a full database backup
backup_full() {
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/$DB_NAME_full_$TIMESTAMP.dump"
    echo "Starting full backup of database '$DB_NAME' to '$BACKUP_FILE'..."
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc -v "$DB_NAME" > "$BACKUP_FILE"
    if [ $? -eq 0 ]; then
        echo "Full backup successful: $BACKUP_FILE"
    else
        echo "Error: Full backup failed."
        exit 1
    fi
}

# Function to perform a schema-only backup
backup_schema_only() {
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$SCHEMA_ONLY_DIR/$DB_NAME_schema_$TIMESTAMP.sql"
    echo "Starting schema-only backup of database '$DB_NAME' to '$BACKUP_FILE'..."
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -s -v "$DB_NAME" > "$BACKUP_FILE"
    if [ $? -eq 0 ]; then
        echo "Schema-only backup successful: $BACKUP_FILE"
    else
        echo "Error: Schema-only backup failed."
        exit 1
    fi
}

# Function to perform a data-only backup
backup_data_only() {
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$DATA_ONLY_DIR/$DB_NAME_data_$TIMESTAMP.dump"
    echo "Starting data-only backup of database '$DB_NAME' to '$BACKUP_FILE'..."
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc -a -v "$DB_NAME" > "$BACKUP_FILE"
    if [ $? -eq 0 ]; then
        echo "Data-only backup successful: $BACKUP_FILE"
    else
        echo "Error: Data-only backup failed."
        exit 1
    fi
}

# Function to restore a database from a full backup file
restore_full() {
    if [ -z "$1" ]; then
        echo "Usage: restore_full <backup_file>"
        echo "Example: restore_full backups/vkyc_db_full_20231027_100000.dump"
        exit 1
    fi
    BACKUP_FILE="$1"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file '$BACKUP_FILE' not found."
        exit 1
    fi

    echo "WARNING: This will drop and recreate database '$DB_NAME'. All existing data will be lost."
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    echo "Dropping and recreating database '$DB_NAME'..."
    # Connect to postgres database to drop/create the target database
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

    if [ $? -ne 0 ]; then
        echo "Error: Failed to drop or create database '$DB_NAME'."
        exit 1
    fi

    echo "Starting restore of database '$DB_NAME' from '$BACKUP_FILE'..."
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v "$BACKUP_FILE"
    if [ $? -eq 0 ]; then
        echo "Restore successful."
    else
        echo "Error: Restore failed."
        exit 1
    fi
}

# Function to restore schema only
restore_schema_only() {
    if [ -z "$1" ]; then
        echo "Usage: restore_schema_only <schema_sql_file>"
        echo "Example: restore_schema_only backups/schema_only/vkyc_db_schema_20231027_100000.sql"
        exit 1
    fi
    SCHEMA_FILE="$1"

    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Schema file '$SCHEMA_FILE' not found."
        exit 1
    fi

    echo "WARNING: This will apply schema from '$SCHEMA_FILE' to '$DB_NAME'. Existing tables might be affected."
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    echo "Applying schema from '$SCHEMA_FILE' to '$DB_NAME'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_FILE"
    if [ $? -eq 0 ]; then
        echo "Schema restore successful."
    else
        echo "Error: Schema restore failed."
        exit 1
    fi
}

# Function to restore data only (assumes schema already exists)
restore_data_only() {
    if [ -z "$1" ]; then
        echo "Usage: restore_data_only <data_dump_file>"
        echo "Example: restore_data_only backups/data_only/vkyc_db_data_20231027_100000.dump"
        exit 1
    fi
    DATA_FILE="$1"

    if [ ! -f "$DATA_FILE" ]; then
        echo "Error: Data file '$DATA_FILE' not found."
        exit 1
    fi

    echo "WARNING: This will restore data from '$DATA_FILE' to '$DB_NAME'. Existing data might be duplicated or overwritten."
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    echo "Restoring data from '$DATA_FILE' to '$DB_NAME'..."
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -a -v "$DATA_FILE"
    if [ $? -eq 0 ]; then
        echo "Data restore successful."
    else
        echo "Error: Data restore failed."
        exit 1
    fi
}

# --- Main Script Logic ---
case "$1" in
    backup_full)
        backup_full
        ;;
    backup_schema)
        backup_schema_only
        ;;
    backup_data)
        backup_data_only
        ;;
    restore_full)
        restore_full "$2"
        ;;
    restore_schema)
        restore_schema_only "$2"
        ;;
    restore_data)
        restore_data_only "$2"
        ;;
    *)
        echo "Usage: $0 {backup_full|backup_schema|backup_data|restore_full <file>|restore_schema <file>|restore_data <file>}"
        echo "  backup_full: Performs a full database backup (schema + data)."
        echo "  backup_schema: Performs a schema-only backup."
        echo "  backup_data: Performs a data-only backup."
        echo "  restore_full <file>: Restores a full database backup. WARNING: Drops existing DB."
        echo "  restore_schema <file>: Restores schema from a SQL file."
        echo "  restore_data <file>: Restores data from a dump file (schema must exist)."
        exit 1
        ;;
esac

# Unset PGPASSWORD for security
unset PGPASSWORD