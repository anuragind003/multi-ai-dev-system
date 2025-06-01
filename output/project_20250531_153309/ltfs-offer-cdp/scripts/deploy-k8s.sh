#!/bin/bash
# deploy-k8s.sh
#
# This script automates the deployment of LTFS Offer CDP microservices to a Kubernetes cluster.
# It supports deployment via Helm charts or raw Kubernetes manifests.
#
# Usage:
#   ./deploy-k8s.sh -e <environment> -t <deployment_type> [-n <namespace>]
#
# Arguments:
#   -e <environment>     : The target environment (e.g., dev, staging, prod).
#   -t <deployment_type> : The deployment method (helm or k8s).
#   -n <namespace>       : (Optional) The Kubernetes namespace to deploy to. Defaults to 'ltfs-cdp'.
#
# Examples:
#   Deploy to 'dev' environment using Helm:
#     ./deploy-k8s.sh -e dev -t helm
#
#   Deploy to 'staging' environment using K8s manifests in a custom namespace:
#     ./deploy-k8s.sh -e staging -t k8s -n ltfs-cdp-staging
#
# Prerequisites:
#   - kubectl command-line tool must be installed and configured.
#   - helm command-line tool must be installed (if using -t helm).
#   - Kubernetes cluster access configured in ~/.kube/config.

# --- Configuration ---
set -euo pipefail # Exit immediately if a command exits with a non-zero status,
                  # exit if an unset variable is used, and propagate pipe errors.

# Define script and project root directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")" # Assuming scripts/ is directly under project root

# Application specific variables
APP_NAME="ltfs-offer-cdp"
DEFAULT_NAMESPACE="ltfs-cdp"
DEFAULT_ENVIRONMENT="dev"

# Directory paths relative to PROJECT_ROOT
HELM_CHARTS_BASE_DIR="${PROJECT_ROOT}/helm"
K8S_MANIFESTS_BASE_DIR="${PROJECT_ROOT}/k8s"

# --- Helper Functions ---

# Logs an informational message
log_info() {
  echo "INFO: $1"
}

# Logs an error message and exits
log_error() {
  echo "ERROR: $1" >&2
  exit 1
}

# Logs a success message
log_success() {
  echo "SUCCESS: $1"
}

# Displays script usage
usage() {
  echo "Usage: $0 -e <environment> -t <deployment_type> [-n <namespace>]"
  echo ""
  echo "Arguments:"
  echo "  -e <environment>     : The target environment (e.g., dev, staging, prod)."
  echo "  -t <deployment_type> : The deployment method (helm or k8s)."
  echo "  -n <namespace>       : (Optional) The Kubernetes namespace to deploy to. Defaults to '${DEFAULT_NAMESPACE}'."
  echo ""
  echo "Examples:"
  echo "  $0 -e dev -t helm"
  echo "  $0 -e staging -t k8s -n ltfs-cdp-staging"
  exit 1
}

# Checks if a command exists
check_prerequisite() {
  if ! command -v "$1" &>/dev/null; then
    log_error "$1 is not installed or not in PATH. Please install it to proceed."
  fi
}

# --- Main Script Logic ---

ENVIRONMENT=""
DEPLOYMENT_TYPE=""
NAMESPACE="${DEFAULT_NAMESPACE}"

# Parse command-line arguments
while getopts "e:t:n:" opt; do
  case "${opt}" in
    e) ENVIRONMENT="${OPTARG}" ;;
    t) DEPLOYMENT_TYPE="${OPTARG}" ;;
    n) NAMESPACE="${OPTARG}" ;;
    *) usage ;;
  esoc
done
shift $((OPTIND - 1))

# Validate required arguments
if [[ -z "${ENVIRONMENT}" || -z "${DEPLOYMENT_TYPE}" ]]; then
  log_error "Missing required arguments. Environment (-e) and Deployment Type (-t) are mandatory."
  usage
fi

# Validate deployment type
if [[ "${DEPLOYMENT_TYPE}" != "helm" && "${DEPLOYMENT_TYPE}" != "k8s" ]]; then
  log_error "Invalid deployment type: '${DEPLOYMENT_TYPE}'. Must be 'helm' or 'k8s'."
  usage
fi

log_info "Starting Kubernetes deployment for '${APP_NAME}'..."
log_info "  Environment: ${ENVIRONMENT}"
log_info "  Namespace:   ${NAMESPACE}"
log_info "  Type:        ${DEPLOYMENT_TYPE}"

# Ensure the target namespace exists. If it doesn't exist, create it.
log_info "Checking/creating Kubernetes namespace '${NAMESPACE}'..."
if ! kubectl get namespace "${NAMESPACE}" &>/dev/null; then
  log_info "Namespace '${NAMESPACE}' not found. Creating it..."
  if ! kubectl create namespace "${NAMESPACE}"; then
    log_error "Failed to create namespace '${NAMESPACE}'. Ensure you have sufficient permissions."
  fi
else
  log_info "Namespace '${NAMESPACE}' already exists."
fi

# --- Perform Deployment based on type ---

if [[ "${DEPLOYMENT_TYPE}" == "helm" ]]; then
  check_prerequisite "helm"
  log_info "Deploying using Helm charts from '${HELM_CHARTS_BASE_DIR}'..."

  if [[ ! -d "${HELM_CHARTS_BASE_DIR}" ]]; then
    log_error "Helm charts base directory not found: '${HELM_CHARTS_BASE_DIR}'. Please ensure it exists and contains your charts."
  fi

  # Iterate through each subdirectory in the Helm charts base directory, treating each as a chart.
  # This assumes each microservice or component has its own Helm chart directory.
  found_charts=false
  for CHART_PATH in "${HELM_CHARTS_BASE_DIR}"/*/; do
    if [[ -d "${CHART_PATH}" ]]; then
      found_charts=true
      CHART_NAME=$(basename "${CHART_PATH}")
      # Helm release names are typically prefixed with the application name for clarity.
      HELM_RELEASE_NAME="${APP_NAME}-${CHART_NAME}"
      VALUES_FILE="${CHART_PATH}/values-${ENVIRONMENT}.yaml"

      log_info "Deploying Helm chart: '${CHART_NAME}' (Release: '${HELM_RELEASE_NAME}')"

      HELM_COMMAND="helm upgrade --install ${HELM_RELEASE_NAME} ${CHART_PATH} --namespace ${NAMESPACE}"

      # If an environment-specific values file exists, use it.
      if [[ -f "${VALUES_FILE}" ]]; then
        log_info "  Using environment-specific values file: ${VALUES_FILE}"
        HELM_COMMAND+=" -f ${VALUES_FILE}"
      else
        log_info "  No environment-specific values file found at ${VALUES_FILE}. Using default values from chart."
      fi

      # Execute the Helm command.
      if eval "${HELM_COMMAND}"; then
        log_success "Successfully deployed Helm chart '${CHART_NAME}'."
      else
        log_error "Failed to deploy Helm chart '${CHART_NAME}'. Please review the Helm output above for details."
      fi
    fi
  done

  if ! ${found_charts}; then
    log_error "No Helm charts found in '${HELM_CHARTS_BASE_DIR}'. Please ensure your charts are correctly placed."
  fi

elif [[ "${DEPLOYMENT_TYPE}" == "k8s" ]]; then
  check_prerequisite "kubectl"
  K8S_ENV_MANIFESTS_DIR="${K8S_MANIFESTS_BASE_DIR}/${ENVIRONMENT}"
  log_info "Deploying using Kubernetes manifests from '${K8S_ENV_MANIFESTS_DIR}'..."

  if [[ ! -d "${K8S_ENV_MANIFESTS_DIR}" ]]; then
    log_error "Kubernetes manifests directory for environment '${ENVIRONMENT}' not found: '${K8S_ENV_MANIFESTS_DIR}'. Please ensure it exists and contains your manifests."
  fi

  # Apply all YAML files in the specified environment directory.
  # The -R flag ensures recursive application in case of subdirectories within the environment folder.
  log_info "Applying manifests from '${K8S_ENV_MANIFESTS_DIR}' to namespace '${NAMESPACE}'..."
  if kubectl apply -f "${K8S_ENV_MANIFESTS_DIR}" --namespace "${NAMESPACE}"; then
    log_success "Successfully applied Kubernetes manifests from '${K8S_ENV_MANIFESTS_DIR}'."
  else
    log_error "Failed to apply Kubernetes manifests from '${K8S_ENV_MANIFESTS_DIR}'. Please review the kubectl output above for details."
  fi

fi

log_success "Kubernetes deployment process completed for '${APP_NAME}'."
exit 0