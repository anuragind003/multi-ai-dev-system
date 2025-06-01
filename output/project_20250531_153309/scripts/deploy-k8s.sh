#!/bin/bash

# deploy-k8s.sh
#
# Shell script to apply Kubernetes manifests for the LTFS Offer CDP system.
# This script automates the deployment of Kubernetes resources (Deployments, Services, ConfigMaps, etc.)
# by applying all YAML files found in a specified directory.
#
# Usage:
#   ./deploy-k8s.sh [OPTIONS]
#
# Options:
#   -d, --dir <path>      Directory containing Kubernetes YAML manifests.
#                         Defaults to '../k8s' relative to the script's location.
#   -n, --namespace <name> Kubernetes namespace to deploy to.
#                         Defaults to 'ltfs-cdp'.
#   -c, --context <name>  Kubernetes context to use.
#                         If not specified, the current kubectl context will be used.
#   -y, --yes             Skip confirmation prompt and proceed with deployment.
#   -h, --help            Display this help message.
#
# Dependencies:
#   - kubectl: Kubernetes command-line tool must be installed and configured.

# --- Configuration ---
# Default directory for Kubernetes manifests, relative to the script's location.
# Assumes a project structure like:
# project-root/
# ├── scripts/
# │   └── deploy-k8s.sh
# └── k8s/
#     └── ... (your YAML files)
DEFAULT_K8S_MANIFESTS_DIR="$(dirname "$0")/../k8s"
# Default Kubernetes namespace for the LTFS Offer CDP system.
DEFAULT_K8S_NAMESPACE="ltfs-cdp"

# Variables to store parsed arguments
K8S_MANIFESTS_DIR=""
K8S_NAMESPACE=""
K8S_CONTEXT=""
SKIP_CONFIRMATION=false

# --- Functions ---

# Function to print usage information for the script.
print_usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dir <path>      Directory containing Kubernetes YAML manifests."
    echo "                        Defaults to '${DEFAULT_K8S_MANIFESTS_DIR}'."
    echo "  -n, --namespace <name> Kubernetes namespace to deploy to."
    echo "                        Defaults to '${DEFAULT_K8S_NAMESPACE}'."
    echo "  -c, --context <name>  Kubernetes context to use."
    echo "                        If not specified, the current kubectl context will be used."
    echo "  -y, --yes             Skip confirmation prompt and proceed with deployment."
    echo "  -h, --help            Display this help message."
    echo ""
    echo "Example:"
    echo "  ./deploy-k8s.sh -d ../k8s/dev -n ltfs-cdp-dev"
    echo "  ./deploy-k8s.sh --context my-cluster-prod -y"
}

# Function to check for required command-line tools (dependencies).
check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        error_exit "'kubectl' command not found. Please install kubectl and ensure it's in your PATH."
    fi
    if ! command -v realpath &> /dev/null; then
        echo "Warning: 'realpath' command not found. Path resolution might be less robust." >&2
        echo "Consider installing 'coreutils' (Linux) or 'brew install coreutils' (macOS)." >&2
    fi
}

# Function to display an error message and exit the script with a non-zero status.
error_exit() {
    echo "Error: $1" >&2
    exit 1
}

# --- Main Script Logic ---

# Set strict error handling:
# -e: Exit immediately if a command exits with a non-zero status.
# -u: Treat unset variables as an error when substituting.
# -o pipefail: The return value of a pipeline is the status of the last command to exit with a non-zero status,
#              or zero if all commands in the pipeline exit successfully.
set -euo pipefail

# Parse command-line arguments using a while loop and case statement.
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -d|--dir)
            K8S_MANIFESTS_DIR="$2"
            shift # Consume argument value
            ;;
        -n|--namespace)
            K8S_NAMESPACE="$2"
            shift # Consume argument value
            ;;
        -c|--context)
            K8S_CONTEXT="$2"
            shift # Consume argument value
            ;;
        -y|--yes)
            SKIP_CONFIRMATION=true
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            print_usage
            exit 1
            ;;
    esac
    shift # Consume argument name (or value if not shifted above)
done

# Apply default values if not provided via command-line arguments.
if [[ -z "$K8S_MANIFESTS_DIR" ]]; then
    K8S_MANIFESTS_DIR="$DEFAULT_K8S_MANIFESTS_DIR"
fi

if [[ -z "$K8S_NAMESPACE" ]]; then
    K8S_NAMESPACE="$DEFAULT_K8S_NAMESPACE"
fi

# --- Pre-deployment Checks ---
check_dependencies

# Resolve the absolute path for the manifests directory.
# This makes the script more robust to how the directory path is provided (relative/absolute).
if command -v realpath &> /dev/null; then
    K8S_MANIFESTS_DIR=$(realpath "$K8S_MANIFESTS_DIR") || error_exit "Invalid manifests directory path: $K8S_MANIFESTS_DIR"
fi

# Verify that the specified Kubernetes manifests directory exists.
if [[ ! -d "$K8S_MANIFESTS_DIR" ]]; then
    error_exit "Kubernetes manifests directory not found: $K8S_MANIFESTS_DIR"
fi

# Display deployment parameters to the user for verification.
echo "--- Kubernetes Deployment Parameters ---"
echo "Manifests Directory: ${K8S_MANIFESTS_DIR}"
echo "Target Namespace:    ${K8S_NAMESPACE}"
if [[ -n "$K8S_CONTEXT" ]]; then
    echo "Kubernetes Context:  ${K8S_CONTEXT}"
else
    echo "Kubernetes Context:  (Using current kubectl context)"
fi
echo "--------------------------------------"
echo ""

# Confirmation prompt before proceeding with the deployment.
# This is a safety measure to prevent accidental deployments, especially in production environments.
if ! "$SKIP_CONFIRMATION"; then
    read -rp "Do you want to proceed with the Kubernetes deployment? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled by user."
        exit 0
    fi
fi

# --- Deployment Execution ---
echo "Starting Kubernetes deployment..."
echo "Applying manifests from: ${K8S_MANIFESTS_DIR}"

# Find all YAML files (.yaml or .yml extensions) in the specified directory and its subdirectories.
# The 'sort' command helps ensure a consistent order of application, though kubectl is generally
# smart enough to handle dependencies.
find "${K8S_MANIFESTS_DIR}" -type f \( -name "*.yaml" -o -name "*.yml" \) | sort | while read -r manifest_file; do
    echo "Applying: ${manifest_file}"

    # Construct the kubectl command as an array for safer execution (avoids issues with spaces/special chars).
    KUBECTL_CMD_ARGS=( "apply" "-f" "${manifest_file}" "-n" "${K8S_NAMESPACE}" )
    if [[ -n "$K8S_CONTEXT" ]]; then
        KUBECTL_CMD_ARGS+=( "--context" "${K8S_CONTEXT}" )
    fi

    # Execute the kubectl command.
    # If kubectl fails for any manifest, the script will exit due to 'set -e'.
    kubectl "${KUBECTL_CMD_ARGS[@]}" || {
        echo "Error applying ${manifest_file}. Aborting deployment." >&2
        exit 1
    }
done

echo ""
echo "Kubernetes deployment completed successfully for namespace '${K8S_NAMESPACE}'."
echo "You can check the status using: kubectl get all -n ${K8S_NAMESPACE}"
if [[ -n "$K8S_CONTEXT" ]]; then
    echo "Or if a context was specified: kubectl get all -n ${K8S_NAMESPACE} --context ${K8S_CONTEXT}"
fi

exit 0