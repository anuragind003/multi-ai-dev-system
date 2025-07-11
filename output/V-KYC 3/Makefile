.PHONY: setup dev build test lint format perf-test deploy backup restore healthcheck scan clean help

# --- Variables ---
DOCKER_COMPOSE_DEV := docker-compose.yml
DOCKER_COMPOSE_PROD := docker-compose.prod.yml
BACKEND_DIR := backend
FRONTEND_DIR := frontend
TERRAFORM_DIR := terraform
SCRIPTS_DIR := scripts
PYTHON := python3
PIP := pip3
PYTEST := pytest
LOCUST := locust
PYLINT := pylint
BLACK := black
FLAKE8 := flake8
MYPY := mypy
TRIVY := trivy

# --- General Commands ---
help:
	@echo "Available commands:"
	@echo "  make setup         - Install Python dependencies."
	@echo "  make dev           - Start development environment using Docker Compose."
	@echo "  make build         - Build Docker images for backend and frontend."
	@echo "  make test          - Run all unit and integration tests."
	@echo "  make lint          - Run code linters (Pylint, Flake8, MyPy)."
	@echo "  make format        - Format code using Black."
	@echo "  make perf-test     - Run performance tests using Locust."
	@echo "  make deploy        - Deploy the application to production (requires setup)."
	@echo "  make backup        - Run database backup script."
	@echo "  make restore       - Run database restore script."
	@echo "  make healthcheck   - Check application health endpoint."
	@echo "  make scan          - Run Docker image vulnerability scan."
	@echo "  make clean         - Clean up build artifacts and Docker resources."

# --- Development & Setup ---
setup:
	@echo "Installing Python dependencies..."
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "Python dependencies installed."

dev:
	@echo "Starting development environment..."
	docker-compose -f $(DOCKER_COMPOSE_DEV) up --build -d
	@echo "Development environment started. Access backend at http://localhost:8000"

# --- Build ---
build:
	@echo "Building Docker images..."
	docker-compose -f $(DOCKER_COMPOSE_DEV) build
	@echo "Docker images built."

# --- Testing ---
test: unit-test integration-test
	@echo "All tests passed."

unit-test:
	@echo "Running unit tests..."
	$(PYTEST) $(BACKEND_DIR)/tests/unit

integration-test:
	@echo "Running integration tests..."
	# Ensure DB is up for integration tests
	docker-compose -f $(DOCKER_COMPOSE_DEV) up -d db
	@echo "Waiting for DB to be ready..."
	@for i in $$(seq 1 10); do \
		nc -z localhost 5432 && echo "DB ready" && break; \
		echo "Waiting for DB..."; \
		sleep 5; \
	done
	DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/mydatabase" $(PYTEST) $(BACKEND_DIR)/tests/integration
	docker-compose -f $(DOCKER_COMPOSE_DEV) stop db # Stop DB after tests

perf-test:
	@echo "Running performance tests..."
	docker-compose -f $(DOCKER_COMPOSE_DEV) up -d backend db # Start backend for perf tests
	@echo "Waiting for backend to be ready..."
	@for i in $$(seq 1 10); do \
		curl -f http://localhost:8000/health && echo "Backend ready" && break; \
		echo "Waiting for backend..."; \
		sleep 5; \
	done
	$(LOCUST) -f $(BACKEND_DIR)/tests/performance/locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 30s --headless --csv=perf_report
	docker-compose -f $(DOCKER_COMPOSE_DEV) stop backend db # Stop backend after tests
	@echo "Performance test report generated: perf_report.csv"

# --- Code Quality ---
lint:
	@echo "Running linters..."
	$(PYLINT) $(BACKEND_DIR)/app
	$(FLAKE8) $(BACKEND_DIR)/app
	$(MYPY) $(BACKEND_DIR)/app

format:
	@echo "Formatting code with Black..."
	$(BLACK) $(BACKEND_DIR)/app $(BACKEND_DIR)/tests
	@echo "Code formatted."

scan:
	@echo "Running Docker image vulnerability scan with Trivy..."
	docker build -t temp-fastapi-image -f $(BACKEND_DIR)/Dockerfile.backend .
	$(TRIVY) image --severity CRITICAL,HIGH --ignore-unfixed temp-fastapi-image
	docker rmi temp-fastapi-image
	@echo "Vulnerability scan complete."

# --- Deployment & Operations ---
deploy:
	@echo "Deploying application to production..."
	# This command would typically trigger your cloud deployment (e.g., Terraform, Kubernetes, Ansible)
	# Example: cd $(TERRAFORM_DIR) && terraform init && terraform apply -auto-approve
	# Example: $(SCRIPTS_DIR)/deploy.sh production
	@echo "Deployment initiated. Check your CI/CD pipeline or cloud console for status."

backup:
	@echo "Running database backup..."
	$(SCRIPTS_DIR)/backup.sh
	@echo "Database backup complete."

restore:
	@echo "Running database restore..."
	$(SCRIPTS_DIR)/restore.sh
	@echo "Database restore complete."

healthcheck:
	@echo "Checking application health..."
	curl -f http://localhost:8000/health || { echo "Health check failed!"; exit 1; }
	@echo "Application is healthy."

# --- Cleanup ---
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose -f $(DOCKER_COMPOSE_DEV) down --volumes --rmi all
	@echo "Removing Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -f perf_report*.csv
	@echo "Cleanup complete."