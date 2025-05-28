#!/bin/bash

# This script runs database migrations for the Flask application using Flask-Migrate.
# It ensures the necessary environment variables are set before executing the migration command.

echo "Starting database migrations..."

# Set FLASK_APP to the module that initializes the Flask application and Flask-Migrate.
# Based on the project context, backend/utils/__init__.py is where Flask-Migrate is initialized.
export FLASK_APP=backend/utils/__init__.py

# Set FLASK_ENV for context (e.g., development, production).
# This can be overridden by the environment where the script is run.
# Defaulting to 'development' if not explicitly set.
export FLASK_ENV=${FLASK_ENV:-development}

# The DATABASE_URL is expected to be set in the environment where this script is run
# (e.g., by Docker Compose, Kubernetes, or manually).
# The Flask application itself has a fallback for DATABASE_URL if it's not set.
# We will echo a warning if it's not set here, but the app might still run with its default.
if [ -z "$DATABASE_URL" ]; then
  echo "Warning: DATABASE_URL environment variable is not explicitly set. The application will use its default configuration."
  echo "         Ensure your database connection string is correctly configured for production environments."
fi

echo "FLASK_APP set to: $FLASK_APP"
echo "FLASK_ENV set to: $FLASK_ENV"

# Run the Flask-Migrate upgrade command.
# This command applies all pending migrations to the database.
flask db upgrade

# Check the exit status of the 'flask db upgrade' command.
if [ $? -eq 0 ]; then
  echo "Database migrations completed successfully."
else
  echo "Error: Database migrations failed. Please check the logs above for details."
  exit 1 # Exit with a non-zero status to indicate failure
fi