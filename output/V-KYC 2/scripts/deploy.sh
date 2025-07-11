#!/bin/bash

# This script automates the deployment of the FastAPI ELK stack using Docker Compose.
# It's designed for a simple server (e.g., the EC2 instance provisioned by Terraform).
# For production, consider Kubernetes, ECS, or more robust orchestration.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
# Replace with your actual Docker Hub username and image name
DOCKER_USERNAME="your_docker_username"
IMAGE_NAME="fastapi-elk-app"
# Tag to deploy (e.g., 'latest' or a specific Git SHA)
DEPLOY_TAG="latest"

# --- Functions ---
log_info() {
  echo -e "\n\033[0;32m[INFO]\033[0m $1"
}

log_warn() {
  echo -e "\n\033[0;33m[WARN]\033[0m $1"
}

log_error() {
  echo -e "\n\033[0;31m[ERROR]\033[0m $1"
  exit 1
}

check_docker_compose() {
  if ! command -v docker-compose &> /dev/null; then
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
      log_error "Docker Compose (v1 or v2) is not installed. Please install it to proceed."
    fi
  fi
}

# --- Main Deployment Logic ---
log_info "Starting FastAPI ELK Stack Deployment..."

# 1. Check for Docker and Docker Compose
check_docker_compose

# 2. Pull the latest Docker image for the FastAPI app
log_info "Pulling latest application Docker image: ${DOCKER_USERNAME}/${IMAGE_NAME}:${DEPLOY_TAG}"
docker pull "${DOCKER_USERNAME}/${IMAGE_NAME}:${DEPLOY_TAG}" || log_error "Failed to pull Docker image."

# 3. Stop and remove existing containers (if any)
log_info "Stopping and removing existing Docker containers..."
# Use `docker compose` for v2, `docker-compose` for v1
if command -v docker compose &> /dev/null; then
  docker compose down || log_warn "No existing containers to stop or failed to stop gracefully."
else
  docker-compose down || log_warn "No existing containers to stop or failed to stop gracefully."
fi

# 4. Clean up old Docker images (optional, but good for disk space)
log_info "Cleaning up old Docker images..."
docker image prune -f || log_warn "Failed to prune old images."

# 5. Copy environment variables (if not using Docker secrets)
# In a real production setup, you'd use Docker secrets or a dedicated secrets manager.
# For this demo, we assume .env is present or created.
if [ ! -f ".env" ]; then
  log_warn ".env file not found. Using .env.template. Please configure your environment variables."
  cp .env.template .env
fi

# 6. Deploy the stack using Docker Compose
log_info "Deploying the ELK stack and FastAPI application..."
if command -v docker compose &> /dev/null; then
  docker compose up -d --build # --build ensures latest image is used if context changed
else
  docker-compose up -d --build
fi

# 7. Verify deployment
log_info "Verifying deployment status..."
sleep 10 # Give services some time to start
if command -v docker compose &> /dev/null; then
  docker compose ps
  if [ "$(docker compose ps -q | wc -l)" -lt 4 ]; then # Expecting 4 services: app, es, ls, kb
    log_error "Not all services are running. Check 'docker compose logs' for details."
  fi
else
  docker-compose ps
  if [ "$(docker-compose ps -q | wc -l)" -lt 4 ]; then
    log_error "Not all services are running. Check 'docker-compose logs' for details."
  fi
fi

log_info "Deployment successful!"
log_info "FastAPI app should be accessible on port 8000."
log_info "Kibana should be accessible on port 5601."
log_info "Elasticsearch on 9200, Logstash on 5000 (TCP) and 9600 (monitoring)."

# --- Rollback Procedure (Manual Example) ---
# If deployment fails, you would manually revert to the previous working image/tag.
# Example:
# docker pull "${DOCKER_USERNAME}/${IMAGE_NAME}:<PREVIOUS_GOOD_TAG>"
# docker tag "${DOCKER_USERNAME}/${IMAGE_NAME}:<PREVIOUS_GOOD_TAG>" "${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
# docker-compose up -d --build
# This script does not automate rollback, but the CI/CD pipeline could.