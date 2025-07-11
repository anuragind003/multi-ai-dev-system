#!/bin/bash

# This script automates the Docker image build, push to ECR, and Terraform deployment.
# It assumes AWS CLI and Terraform are installed and configured.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
AWS_REGION="us-east-1" # Must match terraform/variables.tf and .github/workflows/main.yml
ECR_REPOSITORY_NAME="fastapi-production-service"
TERRAFORM_DIR="terraform"
APP_NAME="fastapi-production-service"

# --- Functions ---
log_info() {
  echo "INFO: $1"
}

log_error() {
  echo "ERROR: $1" >&2
  exit 1
}

# --- Pre-checks ---
command -v docker >/dev/null 2>&1 || log_error "Docker is not installed. Please install Docker."
command -v aws >/dev/null 2>&1 || log_error "AWS CLI is not installed. Please install AWS CLI."
command -v terraform >/dev/null 2>&1 || log_error "Terraform is not installed. Please install Terraform."

# Check if AWS credentials are configured
aws sts get-caller-identity >/dev/null 2>&1 || log_error "AWS CLI is not configured. Please run 'aws configure'."

# --- Build and Push Docker Image ---
log_info "Building Docker image..."
DOCKER_IMAGE_TAG=$(git rev-parse --short HEAD) # Use short Git commit hash as tag
FULL_IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${DOCKER_IMAGE_TAG}"
LATEST_IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:latest"

docker build -t "${FULL_IMAGE_NAME}" -t "${LATEST_IMAGE_NAME}" . || log_error "Docker build failed."

log_info "Logging in to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" || log_error "ECR login failed."

log_info "Pushing Docker image to ECR..."
docker push "${FULL_IMAGE_NAME}" || log_error "Docker push of tagged image failed."
docker push "${LATEST_IMAGE_NAME}" || log_error "Docker push of latest image failed."

log_info "Docker image pushed: ${FULL_IMAGE_NAME}"

# --- Terraform Deployment ---
log_info "Initializing Terraform..."
cd "${TERRAFORM_DIR}" || log_error "Could not change to Terraform directory: ${TERRAFORM_DIR}"
terraform init || log_error "Terraform init failed."

log_info "Planning Terraform changes..."
terraform plan -out=tfplan.out \
  -var="aws_region=${AWS_REGION}" \
  -var="project_name=${APP_NAME}" \
  -var="environment=production" \
  -var="ecr_repository_name=${ECR_REPOSITORY_NAME}" \
  -var="ecs_cluster_name=${APP_NAME}-cluster" \
  -var="ecs_service_name=${APP_NAME}-service" || log_error "Terraform plan failed."

log_info "Applying Terraform changes..."
terraform apply -auto-approve tfplan.out || log_error "Terraform apply failed."

log_info "Deployment complete!"
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "Application is accessible at: http://${ALB_DNS}"

# --- Rollback Procedure ---
echo ""
echo "--- Rollback Procedure ---"
echo "If you need to rollback, you can do the following:"
echo "1. Revert to a previous commit in your Git repository and re-run the CI/CD pipeline."
echo "2. Manually update the ECS Service to a previous task definition revision via AWS Console or AWS CLI:"
echo "   aws ecs update-service --cluster ${APP_NAME}-cluster --service ${APP_NAME}-service --task-definition ${APP_NAME}-service:<PREVIOUS_REVISION_NUMBER>"
echo "   (Find previous revisions in ECS -> Task Definitions)"
echo "3. If infrastructure changes caused issues, run 'terraform apply' with a previous state or revert changes in Terraform files."
echo "   cd ${TERRAFORM_DIR} && terraform apply -auto-approve <path_to_previous_tfplan.out>"