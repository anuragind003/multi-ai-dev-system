#!/bin/bash

# init_db.sh
# This script initializes the PostgreSQL database for the VKYC system.
# It performs the following steps:
# 1. Reads database connection details from config/database.ini.
# 2. Creates the database and a dedicated user if they don't exist.
# 3. Runs Alembic migrations to set up the schema.
# 4. Seeds the database with initial data for development/testing.

# --- Configuration ---
CONFIG_FILE="config/database.ini"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found."
    echo "Please create it with database connection details."
    exit 1
fi

# Read database credentials from config/database.ini
DB_HOST=$(grep -E '^host=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_PORT=$(grep -E '^port=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_NAME=$(grep -E '^dbname=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_USER=$(grep -E '^user=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
DB_PASSWORD=$(grep -E '^password=' "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]')

# Set PGPASSWORD for non-interactive login for psql and pg_dump/restore
# In a production environment, consider more secure methods like .pgpass file or environment variables managed by orchestrator.
export PGPASSWORD="$DB_PASSWORD"

# --- Functions ---

# Function to check if a database exists
db_exists() {
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -w "$DB_NAME" > /dev/null
}

# Function to check if a user exists
user_exists() {
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1
}

# --- Main Script Logic ---

echo "--- Initializing PostgreSQL Database ---"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"

# 1. Create Database User (if not exists)
echo "1. Checking/Creating database user '$DB_USER'..."
if user_exists; then
    echo "User '$DB_USER' already exists."
else
    echo "Creating user '$DB_USER'..."
    # Connect to the default 'postgres' database to create user
    psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    if [ $? -eq 0 ]; then
        echo "User '$DB_USER' created successfully."
    else
        echo "Error: Failed to create user '$DB_USER'."
        unset PGPASSWORD
        exit 1
    fi
fi

# 2. Create Database (if not exists)
echo "2. Checking/Creating database '$DB_NAME'..."
if db_exists; then
    echo "Database '$DB_NAME' already exists."
    read -p "Do you want to drop and recreate the database (Y/n)? This will delete all data! " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Dropping database '$DB_NAME'..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "DROP DATABASE $DB_NAME WITH (FORCE);"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to drop database '$DB_NAME'."
            unset PGPASSWORD
            exit 1
        fi
        echo "Creating database '$DB_NAME'..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        if [ $? -eq 0 ]; then
            echo "Database '$DB_NAME' recreated successfully."
        else
            echo "Error: Failed to create database '$DB_NAME'."
            unset PGPASSWORD
            exit 1
        fi
    else
        echo "Skipping database recreation. Using existing database."
    fi
else
    echo "Creating database '$DB_NAME'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    if [ $? -eq 0 ]; then
        echo "Database '$DB_NAME' created successfully."
    else
        echo "Error: Failed to create database '$DB_NAME'."
        unset PGPASSWORD
        exit 1
    fi
fi

# 3. Run Alembic Migrations
echo "3. Running Alembic migrations..."
# Ensure alembic.ini is configured to use the correct DB connection string
# For this setup, we assume alembic.ini uses the same config/database.ini
# or has the connection string directly.
# A common pattern is to set the SQLAlchemy URL via environment variable for Alembic.
# Example: export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
# Then alembic.ini uses: sqlalchemy.url = ${DATABASE_URL}
# For simplicity, we'll assume alembic.ini is configured to read from config/database.ini
# or directly uses the connection string.
# If alembic.ini needs to be dynamically updated, a Python script would be better.

# For this example, let's assume alembic.ini is set up to read from the environment or directly.
# Or, we can pass the connection string directly to alembic if it supports it (it does via --url).
# However, the standard way is to configure alembic.ini.
# Let's assume alembic.ini is configured to use the 'postgresql' section of config/database.ini
# or that the connection string is hardcoded in alembic.ini for simplicity of this script.
# For a robust solution, you'd typically pass the connection string or configure alembic.ini dynamically.

# Let's create a dummy alembic.ini for this example to make it runnable.
# In a real project, you'd have a proper alembic setup.
if [ ! -f "alembic.ini" ]; then
    echo "Creating dummy alembic.ini for migration..."
    cat <<EOF > alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
# Add other Alembic configurations as needed
EOF
fi

alembic upgrade head
if [ $? -eq 0 ]; then
    echo "Alembic migrations applied successfully."
else
    echo "Error: Alembic migrations failed."
    unset PGPASSWORD
    exit 1
fi

# 4. Seed Database with Initial Data
echo "4. Seeding database with initial data..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f seed_data.sql
if [ $? -eq 0 ]; then
    echo "Database seeded successfully."
else
    echo "Error: Failed to seed database."
    unset PGPASSWORD
    exit 1
fi

echo "--- Database Initialization Complete ---"

# Unset PGPASSWORD for security
unset PGPASSWORD

# Clean up dummy alembic.ini if created by this script
if [ -f "alembic.ini" ] && grep -q "sqlalchemy.url = postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" alembic.ini; then
    echo "Removing temporary alembic.ini..."
    rm alembic.ini
fi