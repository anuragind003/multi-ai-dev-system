#!/bin/bash
set -euo pipefail

# Source production environment variables if available
if [ -f .env.prod ]; then
  export $(grep -v '^#' .env.prod | xargs)
fi

# --- Deployment Functions ---

deploy_app() {
  echo "--- Starting application deployment ---"

  # Validate required environment variables
  if [ -z "${AWS_REGION}" ] || [ -z "${ECR_REPOSITORY}" ] || [ -z "${APP_IMAGE_TAG}" ]; then
    echo "Error: AWS_REGION, ECR_REPOSITORY, and APP_IMAGE_TAG must be set."
    exit 1
  fi

  # Assume AWS CLI is configured with appropriate credentials on the deployment host
  # and Docker is installed.

  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  ECR_FULL_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${APP_IMAGE_TAG}"
  ECR_LATEST_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

  echo "Attempting to deploy image: ${ECR_FULL_IMAGE}"

  # 1. Login to ECR
  echo "Logging in to ECR..."
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}".dkr.ecr."${AWS_REGION}".amazonaws.com
  echo "ECR login successful."

  # 2. Pull the new Docker image
  echo "Pulling new image: ${ECR_FULL_IMAGE}"
  docker pull "${ECR_FULL_IMAGE}"

  # 3. Stop and remove existing container (if any)
  echo "Stopping and removing existing container (if any)..."
  if docker ps -a --format '{{.Names}}' | grep -q "my-fastapi-app"; then
    docker stop my-fastapi-app
    docker rm my-fastapi-app
  fi

  # 4. Run the new container
  echo "Running new container..."
  # Pass all environment variables from the current shell to the container
  # For production, consider using a tool like AWS ECS/EKS or Kubernetes for orchestration
  # and secure secret management (e.g., AWS Secrets Manager).
  # This example uses `env` to pass all current shell env vars.
  # A more robust solution would explicitly list required vars or use --env-file.
  docker run -d --name my-fastapi-app -p 8000:8000 \
    $(env | grep -E '^(DATABASE_URL|SECRET_KEY|APP_ENV|LOG_LEVEL)' | sed 's/^/-e /') \
    "${ECR_FULL_IMAGE}"

  echo "Container started. Waiting for health check..."

  # 5. Health check (liveness probe)
  # Give the container some time to start up
  sleep 10
  HEALTH_CHECK_URL="http://localhost:8000/health"
  MAX_RETRIES=10
  RETRY_INTERVAL=5

  for i in $(seq 1 $MAX_RETRIES); do
    if curl -f "${HEALTH_CHECK_URL}"; then
      echo "Application health check passed!"
      break
    else
      echo "Health check failed (attempt $i/$MAX_RETRIES). Retrying in ${RETRY_INTERVAL}s..."
      sleep "${RETRY_INTERVAL}"
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
      echo "Error: Application failed health check after multiple retries. Deployment failed."
      # Optional: Rollback to previous image if health check fails
      # rollback_app
      exit 1
    fi
  done

  echo "Deployment successful for image: ${ECR_FULL_IMAGE}"
}

rollback_app() {
  echo "--- Starting application rollback ---"
  # This is a very basic rollback. In a real scenario, you'd manage previous image tags
  # or use orchestration tools' rollback features (e.g., ECS service rollback).

  # Get the previous image tag (e.g., from a deployment history or a specific tag)
  # For simplicity, this example assumes you know the previous good image.
  # In a real system, you'd store the last successful deployment's image tag.
  PREVIOUS_GOOD_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:<PREVIOUS_GOOD_SHA_OR_TAG>"

  if [ -z "${PREVIOUS_GOOD_IMAGE}" ]; then
    echo "Error: No previous good image tag specified for rollback."
    exit 1
  fi

  echo "Attempting to rollback to image: ${PREVIOUS_GOOD_IMAGE}"

  docker pull "${PREVIOUS_GOOD_IMAGE}"
  docker stop my-fastapi-app || true
  docker rm my-fastapi-app || true
  docker run -d --name my-fastapi-app -p 8000:8000 \
    $(env | grep -E '^(DATABASE_URL|SECRET_KEY|APP_ENV|LOG_LEVEL)' | sed 's/^/-e /') \
    "${PREVIOUS_GOOD_IMAGE}"

  echo "Rollback initiated. Please check application health."
}

# --- Database Backup and Recovery Functions ---

backup_rds() {
  echo "--- Starting RDS PostgreSQL backup ---"

  if [ -z "${DB_INSTANCE_IDENTIFIER}" ]; then
    echo "Error: DB_INSTANCE_IDENTIFIER environment variable not set."
    exit 1
  fi

  SNAPSHOT_ID="${DB_INSTANCE_IDENTIFIER}-$(date +%Y-%m-%d-%H-%M-%S)"

  echo "Creating RDS snapshot: ${SNAPSHOT_ID} for instance ${DB_INSTANCE_IDENTIFIER} in region ${AWS_REGION}..."
  aws rds create-db-snapshot \
    --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" \
    --db-snapshot-identifier "${SNAPSHOT_ID}" \
    --region "${AWS_REGION}"

  echo "Snapshot creation initiated. You can monitor its status in the AWS RDS console or with:"
  echo "aws rds describe-db-snapshots --db-snapshot-identifier ${SNAPSHOT_ID} --region ${AWS_REGION}"
  echo "--- RDS PostgreSQL backup complete ---"
}

restore_rds() {
  echo "--- Starting RDS PostgreSQL restore ---"

  if [ "$#" -ne 2 ]; then
    echo "Usage: restore_rds <SNAPSHOT_ID> <NEW_DB_IDENTIFIER>"
    echo "Example: restore_rds fastapi-app-db-2023-10-27-10-00-00 fastapi-app-db-restored"
    exit 1
  fi

  SNAPSHOT_ID="$1"
  NEW_DB_IDENTIFIER="$2"

  if [ -z "${DB_INSTANCE_CLASS}" ] || [ -z "${DB_SUBNET_GROUP_NAME}" ] || [ -z "${DB_SECURITY_GROUP_IDS}" ]; then
    echo "Error: DB_INSTANCE_CLASS, DB_SUBNET_GROUP_NAME, and DB_SECURITY_GROUP_IDS must be set for restore."
    echo "These can be obtained from your Terraform outputs or AWS console."
    exit 1
  fi

  echo "Restoring snapshot ${SNAPSHOT_ID} to new instance ${NEW_DB_IDENTIFIER}..."
  aws rds restore-db-instance-from-db-snapshot \
    --db-snapshot-identifier "${SNAPSHOT_ID}" \
    --db-instance-identifier "${NEW_DB_IDENTIFIER}" \
    --db-instance-class "${DB_INSTANCE_CLASS}" \
    --db-subnet-group-name "${DB_SUBNET_GROUP_NAME}" \
    --vpc-security-group-ids "${DB_SECURITY_GROUP_IDS}" \
    --region "${AWS_REGION}"

  echo "Restore initiated. A new RDS instance '${NEW_DB_IDENTIFIER}' is being created."
  echo "You will need to update your application's DATABASE_URL to point to the new instance's endpoint once it's available."
  echo "--- RDS PostgreSQL restore complete ---"
}

# --- Main script logic ---

case "$1" in
  deploy_app)
    deploy_app
    ;;
  rollback_app)
    rollback_app
    ;;
  backup_rds)
    backup_rds
    ;;
  restore_rds)
    shift # Remove the first argument (command name)
    restore_rds "$@"
    ;;
  *)
    echo "Usage: $0 {deploy_app|rollback_app|backup_rds|restore_rds <SNAPSHOT_ID> <NEW_DB_IDENTIFIER>}"
    exit 1
    ;;
esac