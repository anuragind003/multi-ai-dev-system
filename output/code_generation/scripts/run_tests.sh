#!/bin/bash

# This script runs all tests and code quality checks.
# Designed to be used locally and by the CI/CD pipeline.

set -e # Exit immediately if a command exits with a non-zero status.

log_info() {
  echo "INFO: $1"
}

log_error() {
  echo "ERROR: $1" >&2
  exit 1
}

# --- Pre-checks ---
command -v poetry >/dev/null 2>&1 || log_error "Poetry is not installed. Please install Poetry."

log_info "Installing project dependencies with Poetry..."
poetry install --no-root || log_error "Poetry install failed."

# --- Code Quality Checks ---
log_info "Running Pylint for code quality..."
poetry run pylint app/ || log_error "Pylint found issues."

log_info "Running Black for code formatting check..."
poetry run black --check app/ tests/ || log_error "Black found formatting issues. Run 'poetry run black app/ tests/' to fix."

log_info "Running Isort for import sorting check..."
poetry run isort --check-only app/ tests/ || log_error "Isort found import sorting issues. Run 'poetry run isort app/ tests/' to fix."

# --- Unit Tests ---
log_info "Running Unit Tests..."
poetry run pytest tests/unit/ || log_error "Unit tests failed."

# --- Integration Tests ---
log_info "Building Docker image for Integration Tests..."
docker build -t fastapi-integration-test . || log_error "Docker build for integration tests failed."

log_info "Starting Docker container for Integration Tests..."
docker run -d --name fastapi-app-integration -p 8000:8000 fastapi-integration-test || log_error "Failed to start integration test container."

# Give the container some time to start up and become healthy
log_info "Waiting for API to become healthy (max 30 seconds)..."
for i in $(seq 1 10); do
  if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    log_info "API is healthy."
    break
  fi
  log_info "API not ready yet, waiting 3 seconds..."
  sleep 3
  if [ "$i" -eq 10 ]; then
    log_error "API did not become healthy within the timeout."
  fi
done

log_info "Running Integration Tests..."
# Set API_BASE_URL for integration tests to use
API_BASE_URL="http://localhost:8000" poetry run pytest tests/integration/ || log_error "Integration tests failed."

# --- Cleanup ---
log_info "Stopping and removing integration test container..."
docker stop fastapi-app-integration >/dev/null 2>&1 || true
docker rm fastapi-app-integration >/dev/null 2>&1 || true

log_info "All tests and quality checks passed successfully!"