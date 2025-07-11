#!/bin/bash
# scripts/deploy_and_rollback.sh
# This script handles deployment and rollback of the Dockerized FastAPI application on an EC2 instance.

set -e # Exit immediately if a command exits with a non-zero status.

ACTION=$1
EC2_INSTANCE_IP=$2
EC2_SSH_USER=$3
CI_REGISTRY_IMAGE=$4
CI_COMMIT_SHA=$5 # Only used for 'deploy' action

# Function to log messages
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Ensure SSH key is loaded
ensure_ssh_key() {
  if [ -z "$EC2_PRIVATE_KEY_PATH" ]; then
    log "Error: EC2_PRIVATE_KEY_PATH is not set. Cannot proceed with SSH."
    exit 1
  fi

  if [ ! -f "$EC2_PRIVATE_KEY_PATH" ]; then
    log "Error: SSH private key not found at $EC2_PRIVATE_KEY_PATH."
    exit 1
  fi

  chmod 600 "$EC2_PRIVATE_KEY_PATH" || { log "Error: Failed to set correct permissions for SSH key."; exit 1; }

  # Add key to ssh-agent if not already added
  if ! ssh-add -l | grep -q "$(ssh-keygen -lf "$EC2_PRIVATE_KEY_PATH" | awk '{print $2}')"; then
    eval "$(ssh-agent -s)"
    ssh-add "$EC2_PRIVATE_KEY_PATH" || { log "Error: Failed to add SSH key to agent."; exit 1; }
  fi

  # Add host to known_hosts to avoid interactive prompts
  ssh-keyscan -H "$EC2_INSTANCE_IP" >> ~/.ssh/known_hosts 2>/dev/null || true
}

# Function to execute commands on the remote EC2 instance
remote_exec() {
  local cmd="$1"
  log "Executing remote command: $cmd"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_SSH_USER@$EC2_INSTANCE_IP" "$cmd"
}

# Function to perform health check
health_check() {
  local ip=$1
  local port=8000
  local max_attempts=15
  local attempt=1

  log "Performing health check on http://$ip:$port/health"
  while [ $attempt -le $max_attempts ]; do
    if curl -f "http://$ip:$port/health" > /dev/null 2>&1; then
      log "Health check passed!"
      return 0
    else
      log "Health check failed (attempt $attempt/$max_attempts). Retrying in 10 seconds..."
      sleep 10
      attempt=$((attempt + 1))
    fi
  done
  log "Health check failed after $max_attempts attempts. Deployment may have failed."
  return 1
}

# Deployment function
deploy() {
  local image_tag="$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA"
  local latest_tag="$CI_REGISTRY_IMAGE:latest"

  log "Starting deployment of $image_tag to $EC2_INSTANCE_IP"

  # Store current running image for rollback
  local current_image=$(remote_exec "docker ps --filter 'name=fastapi-app' --format '{{.Image}}' || echo ''")
  if [ -n "$current_image" ]; then
    log "Current running image: $current_image. Storing for potential rollback."
    remote_exec "echo '$current_image' > /tmp/previous_app_image.txt"
  else
    log "No existing container found. This might be the first deployment."
    remote_exec "rm -f /tmp/previous_app_image.txt" # Clear any old rollback info
  fi

  # Pull the new image
  log "Pulling new image: $image_tag"
  remote_exec "docker pull $image_tag" || { log "Error: Failed to pull new Docker image."; exit 1; }

  # Stop and remove old container
  log "Stopping and removing old container (if any)..."
  remote_exec "docker stop fastapi-app || true"
  remote_exec "docker rm fastapi-app || true"

  # Run new container
  log "Running new container: $image_tag"
  remote_exec "docker run -d --name fastapi-app -p 8000:8000 --restart always $image_tag" || { log "Error: Failed to run new Docker container."; exit 1; }

  # Health check
  health_check "$EC2_INSTANCE_IP" || { log "Error: Application health check failed after deployment."; exit 1; }

  # Tag the deployed image as 'latest' on the remote host for easier management
  log "Tagging $image_tag as $latest_tag on remote host."
  remote_exec "docker tag $image_tag $latest_tag"

  log "Deployment successful for $image_tag!"
}

# Rollback function
rollback() {
  local latest_tag="$CI_REGISTRY_IMAGE:latest"
  log "Starting rollback on $EC2_INSTANCE_IP"

  local previous_image=$(remote_exec "cat /tmp/previous_app_image.txt || echo ''")

  if [ -z "$previous_image" ]; then
    log "Error: No previous image found for rollback. Cannot proceed."
    exit 1
  fi

  log "Attempting to rollback to previous image: $previous_image"

  # Pull the previous image (it should already be on the host, but ensure)
  log "Pulling previous image: $previous_image"
  remote_exec "docker pull $previous_image" || { log "Error: Failed to pull previous Docker image."; exit 1; }

  # Stop and remove current container
  log "Stopping and removing current container..."
  remote_exec "docker stop fastapi-app || true"
  remote_exec "docker rm fastapi-app || true"

  # Run previous container
  log "Running previous container: $previous_image"
  remote_exec "docker run -d --name fastapi-app -p 8000:8000 --restart always $previous_image" || { log "Error: Failed to run previous Docker container."; exit 1; }

  # Health check
  health_check "$EC2_INSTANCE_IP" || { log "Error: Application health check failed after rollback."; exit 1; }

  log "Rollback to $previous_image successful!"
}

# Main execution logic
ensure_ssh_key

case "$ACTION" in
  deploy)
    if [ -z "$EC2_INSTANCE_IP" ] || [ -z "$EC2_SSH_USER" ] || [ -z "$CI_REGISTRY_IMAGE" ] || [ -z "$CI_COMMIT_SHA" ]; then
      log "Usage: $0 deploy <EC2_INSTANCE_IP> <EC2_SSH_USER> <CI_REGISTRY_IMAGE> <CI_COMMIT_SHA>"
      exit 1
    fi
    deploy
    ;;
  rollback)
    if [ -z "$EC2_INSTANCE_IP" ] || [ -z "$EC2_SSH_USER" ] || [ -z "$CI_REGISTRY_IMAGE" ]; then
      log "Usage: $0 rollback <EC2_INSTANCE_IP> <EC2_SSH_USER> <CI_REGISTRY_IMAGE>"
      exit 1
    fi
    rollback
    ;;
  *)
    log "Invalid action: $ACTION. Use 'deploy' or 'rollback'."
    exit 1
    ;;
esac