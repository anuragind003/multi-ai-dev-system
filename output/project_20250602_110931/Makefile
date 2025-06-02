# Makefile for Simple Task Tracker

# --- Configuration Variables ---
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
FLASK = $(VENV_DIR)/bin/flask
PYTEST = $(VENV_DIR)/bin/pytest
BLACK = $(VENV_DIR)/bin/black
FLAKE8 = $(VENV_DIR)/bin/flake8

# Flask application module path (e.g., src/app.py -> src.app)
# This tells Flask where to find your application instance.
FLASK_APP_MODULE = src.app
# Set Flask environment for development. This affects debug mode, error handling, etc.
FLASK_ENV = development
# SQLite database path for development (relative to project root).
# This is where the SQLite database file will be created.
SQLITE_DB_PATH = instance/app.db
# Directory for Flask-Migrate migrations (relative to project root).
# This folder will contain your database migration scripts.
MIGRATIONS_DIR = src/migrations

# --- Phony Targets ---
# .PHONY declares targets that do not correspond to actual files.
# This ensures that make always runs the commands associated with these targets,
# even if a file with the same name exists.
.PHONY: all setup install run-backend test lint format db-init db-migrate db-upgrade db-downgrade db-seed clean help

# Default target: If 'make' is run without any arguments, it will display the help message.
all: help

# --- Development Setup ---

# setup: Creates a virtual environment and installs all project dependencies.
# This is typically the first command to run after cloning the repository.
setup: $(VENV_DIR)
	@echo "--- Setting up virtual environment and installing dependencies ---"
	$(PIP) install -r requirements.txt
	@echo "--- Setup complete. Use 'source $(VENV_DIR)/bin/activate' to activate the venv. ---"

# Target to create the virtual environment if it doesn't exist.
# This is a prerequisite for 'setup' and 'install'.
$(VENV_DIR):
	@echo "Creating virtual environment at $(VENV_DIR)..."
	python3 -m venv $(VENV_DIR)
	@echo "Virtual environment created."

# install: Installs or reinstalls project dependencies from requirements.txt.
# Useful if requirements.txt changes or to ensure all dependencies are up-to-date.
install: $(VENV_DIR)
	@echo "--- Installing/reinstalling Python dependencies ---"
	$(PIP) install -r requirements.txt
	@echo "--- Dependencies installed. ---"

# --- Application Execution ---

# run-backend: Runs the Flask development server.
# The FLASK_APP and FLASK_ENV environment variables are set for the command.
run-backend: $(VENV_DIR)
	@echo "--- Running Flask backend development server ---"
	@echo "FLASK_APP=$(FLASK_APP_MODULE)"
	@echo "FLASK_ENV=$(FLASK_ENV)"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) run --debug

# --- Testing ---

# test: Runs all unit and integration tests using pytest.
# Sets FLASK_ENV to 'testing' to ensure tests run with appropriate configurations (e.g., in-memory DB).
test: $(VENV_DIR)
	@echo "--- Running tests ---"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=testing $(PYTEST)

# --- Code Quality ---

# lint: Checks code style and potential errors using flake8.
# Scans the 'src/' and 'tests/' directories for issues.
lint: $(VENV_DIR)
	@echo "--- Running linter (flake8) ---"
	$(FLAKE8) src/ tests/

# format: Formats code using black, an opinionated code formatter.
# Applies formatting to 'src/' and 'tests/' directories.
format: $(VENV_DIR)
	@echo "--- Formatting code (black) ---"
	$(BLACK) src/ tests/

# --- Database Management (Flask-Migrate) ---

# db-init: Initializes the migration repository.
# This command should be run only once per project to set up the migrations directory.
db-init: $(VENV_DIR)
	@echo "--- Initializing database migrations repository ---"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) db init --directory $(MIGRATIONS_DIR)
	@echo "Migration repository initialized. Review $(MIGRATIONS_DIR) for changes."

# db-migrate: Generates a new migration script based on changes detected in your models.
# It prompts the user for a message to describe the migration.
db-migrate: $(VENV_DIR)
	@echo "--- Generating new database migration script ---"
	@read -p "Enter a migration message: " MESSAGE; \
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) db migrate -m "$$MESSAGE" --directory $(MIGRATIONS_DIR)
	@echo "Migration script generated. Review it before upgrading."

# db-upgrade: Applies pending database migrations to the database.
# This updates the database schema to the latest version defined by your migration scripts.
db-upgrade: $(VENV_DIR)
	@echo "--- Applying database migrations ---"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) db upgrade --directory $(MIGRATIONS_DIR)
	@echo "Database migrations applied."

# db-downgrade: Reverts the last applied database migration.
# Use with caution, as downgrading can lead to data loss if not handled properly.
db-downgrade: $(VENV_DIR)
	@echo "--- Reverting last database migration ---"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) db downgrade --directory $(MIGRATIONS_DIR)
	@echo "Last database migration reverted."

# db-seed: Seeds the database with initial data.
# This target assumes a custom Flask CLI command named 'seed-db' is implemented
# in your Flask application (e.g., using @app.cli.command('seed-db')).
db-seed: $(VENV_DIR)
	@echo "--- Seeding database with initial data ---"
	FLASK_APP=$(FLASK_APP_MODULE) FLASK_ENV=$(FLASK_ENV) $(FLASK) seed-db
	@echo "Database seeded."

# --- Cleanup ---

# clean: Removes build artifacts, virtual environment, and cache files.
# This helps in getting a clean slate for development or deployment.
clean:
	@echo "--- Cleaning up project artifacts ---"
	@echo "Removing virtual environment ($(VENV_DIR))..."
	rm -rf $(VENV_DIR)
	@echo "Removing Python cache directories (__pycache__, *.pyc)..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Removing pytest cache (.pytest_cache/)..."
	rm -rf .pytest_cache/
	@echo "Removing instance folder (including SQLite DB: $(SQLITE_DB_PATH))..."
	rm -rf instance/
	@echo "Cleanup complete."

# --- Help ---

# help: Displays available commands and their descriptions.
help:
	@echo "Usage: make <command>"
	@echo ""
	@echo "Available commands:"
	@echo "  setup         : Creates a virtual environment and installs dependencies."
	@echo "  install       : Installs/reinstalls dependencies from requirements.txt."
	@echo "  run-backend   : Runs the Flask development server."
	@echo "  test          : Runs all unit and integration tests."
	@echo "  lint          : Checks code style and potential errors using flake8."
	@echo "  format        : Formats code using black."
	@echo "  db-init       : Initializes the migration repository (run once per project)."
	@echo "  db-migrate    : Generates a new database migration script based on model changes."
	@echo "  db-upgrade    : Applies pending database migrations to the database."
	@echo "  db-downgrade  : Reverts the last applied database migration (use with caution)."
	@echo "  db-seed       : Seeds the database with initial data (requires custom 'flask seed-db' command)."
	@echo "  clean         : Removes virtual environment, cache files, and instance folder (including SQLite DB)."
	@echo "  help          : Displays this help message."