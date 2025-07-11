#!/bin/bash

# deploy.sh - Script for deploying the FastAPI application to a production server.
# This script assumes Docker and Docker Compose are already installed on the target server.

# Configuration
APP_NAME="fastapi-app"
DEPLOY_DIR="/opt/$APP_NAME"
DOCKER_REGISTRY="your-docker-registry" # e.g., ghcr.io/your-org or docker.io/your-username
IMAGE_NAME="$DOCKER_REGISTRY/$APP_NAME"
PROD_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

# --- Functions ---

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
  log "ERROR: $1"
  exit 1
}

check_prerequisites() {
  log "Checking prerequisites..."
  command -v docker >/dev/null 2>&1 || error_exit "Docker is not installed. Please install Docker."
  command -v docker-compose >/dev/null 2>&1 || error_exit "Docker Compose is not installed. Please install Docker Compose."
  log "Prerequisites met."
}

pull_latest_image() {
  log "Pulling latest Docker image: $IMAGE_NAME:latest"
  docker pull "$IMAGE_NAME:latest" || error_exit "Failed to pull Docker image."
}

deploy_application() {
  log "Deploying application using Docker Compose..."
  # Ensure the deployment directory exists
  mkdir -p "$DEPLOY_DIR"
  cd "$DEPLOY_DIR" || error_exit "Failed to change to deployment directory $DEPLOY_DIR"

  # Copy necessary files (docker-compose.prod.yml, .env.prod, nginx configs, monitoring configs)
  # In a real scenario, these would be managed by a configuration management tool (Ansible, Puppet)
  # or fetched from a secure source. For this example, assume they are present or copied via CI/CD.
  log "Copying deployment files..."
  # Example: cp /path/to/source/docker-compose.prod.yml .
  # Example: cp /path/to/source/.env.prod .
  # Example: cp -r /path/to/source/nginx .
  # Example: cp -r /path/to/source/monitoring .

  # For this demo, we'll assume the CI/CD pipeline has placed these files in $DEPLOY_DIR
  if [ ! -f "$PROD_COMPOSE_FILE" ]; then
    error_exit "$PROD_COMPOSE_FILE not found in $DEPLOY_DIR. Please ensure it's copied."
  fi
  if [ ! -f "$ENV_FILE" ]; then
    error_exit "$ENV_FILE not found in $DEPLOY_DIR. Please ensure it's copied and contains production secrets."
  fi

  # Bring down existing services gracefully
  log "Bringing down existing services..."
  docker-compose -f "$PROD_COMPOSE_FILE" down --remove-orphans

  # Bring up new services
  log "Bringing up new services..."
  docker-compose -f "$PROD_COMPOSE_FILE" up -d --build # --build is for local build, remove if only pulling
  
  log "Waiting for services to stabilize (15 seconds)..."
  sleep 15

  log "Checking service status..."
  docker-compose -f "$PROD_COMPOSE_FILE" ps || error_exit "Docker Compose services failed to start."

  log "Running health check on application..."
  # Assuming the app is exposed on port 80 via Nginx or directly
  curl -f http://localhost/health || error_exit "Application health check failed."
  log "Application health check passed."

  log "Deployment successful!"
}

rollback_application() {
  log "Initiating rollback..."
  cd "$DEPLOY_DIR" || error_exit "Failed to change to deployment directory $DEPLOY_DIR"

  # This is a simplified rollback. A robust rollback would involve:
  # 1. Tagging images with versions (e.g., current_version, previous_version)
  # 2. Storing previous docker-compose files or configurations
  # 3. Reverting to the previous image tag and re-deploying
  # For this example, we'll just restart the services, assuming the previous stable image is available.

  log "Attempting to revert to previous stable state (restarting services)..."
  docker-compose -f "$PROD_COMPOSE_FILE" down --remove-orphans
  # If you had a previous image tag, you'd pull it here:
  # docker pull "$IMAGE_NAME:previous_stable_tag"
  docker-compose -f "$PROD_COMPOSE_FILE" up -d

  log "Rollback initiated. Please verify application status."
}

# --- Main Script Logic ---

case "$1" in
  deploy)
    check_prerequisites
    pull_latest_image
    deploy_application
    ;;
  rollback)
    rollback_application
    ;;
  *)
    echo "Usage: $0 {deploy|rollback}"
    exit 1
    ;;
esac