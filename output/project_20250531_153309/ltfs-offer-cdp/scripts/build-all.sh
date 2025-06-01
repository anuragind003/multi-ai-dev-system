#!/bin/bash

# build-all.sh
#
# This script automates the build process for all microservices within the LTFS Offer CDP project.
# It performs the following steps for each microservice:
# 1. Builds the Maven artifact (JAR file).
# 2. Builds the Docker image.
#
# Usage:
#   Run this script from the 'ltfs-offer-cdp/scripts' directory:
#   ./build-all.sh
#
# Prerequisites:
# - Maven must be installed and available in the PATH.
# - Docker must be installed and running.
# - Each microservice directory must contain a pom.xml and a Dockerfile.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Define the list of microservice directories relative to the project root.
# These names should match the directory names of your microservices.
MICROSERVICES=(
    "customer-profile-service"
    "offer-management-service"
    "data-validation-service"
    "deduplication-service"
    "event-processor-service"
)

# Define the base Docker image name prefix.
DOCKER_IMAGE_PREFIX="ltfs-cdp"

# --- Helper Functions ---

# Function to check if a command exists
command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# --- Main Script Logic ---

echo "==================================================="
echo " LTFS Offer CDP - Build All Microservices Script "
echo "==================================================="

# Check for prerequisites
echo "Checking prerequisites..."
if ! command_exists mvn; then
    echo "Error: Maven is not installed or not in your PATH. Please install Maven."
    exit 1
fi
if ! command_exists docker; then
    echo "Error: Docker is not installed or not in your PATH. Please install Docker and ensure it's running."
    exit 1
fi
echo "Prerequisites checked: Maven and Docker found."
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the project root directory (one level up from 'scripts')
PROJECT_ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Navigating to project root: $PROJECT_ROOT_DIR"
cd "$PROJECT_ROOT_DIR" || { echo "Error: Could not navigate to project root."; exit 1; }
echo "Current directory: $(pwd)"
echo ""

# Loop through each microservice and build it
for SERVICE_DIR in "${MICROSERVICES[@]}"; do
    echo "---------------------------------------------------"
    echo "Building microservice: $SERVICE_DIR"
    echo "---------------------------------------------------"

    # Check if the service directory exists
    if [ ! -d "$SERVICE_DIR" ]; then
        echo "Error: Microservice directory '$SERVICE_DIR' not found. Skipping."
        continue
    fi

    # Navigate into the service directory
    cd "$SERVICE_DIR" || { echo "Error: Could not navigate to $SERVICE_DIR. Skipping."; continue; }
    echo "Entered directory: $(pwd)"

    # 1. Build Maven artifact
    echo "Building Maven artifact for $SERVICE_DIR..."
    # Use -DskipTests to speed up builds, as tests might be run in a separate CI/CD stage.
    # This command will clean the target directory, compile, and package the JAR.
    if mvn clean install -DskipTests; then
        echo "Maven build successful for $SERVICE_DIR."
    else
        echo "Error: Maven build failed for $SERVICE_DIR. Aborting."
        exit 1
    fi

    # 2. Build Docker image
    echo "Building Docker image for $SERVICE_DIR..."
    # The Docker image name will be ltfs-cdp-<service-name>
    # The Dockerfile is expected to be in the current directory (SERVICE_DIR).
    # It should typically copy the generated JAR from the 'target' directory.
    DOCKER_IMAGE_NAME="${DOCKER_IMAGE_PREFIX}-${SERVICE_DIR}"
    if docker build -t "$DOCKER_IMAGE_NAME" .; then
        echo "Docker image '$DOCKER_IMAGE_NAME' built successfully."
    else
        echo "Error: Docker image build failed for $SERVICE_DIR. Aborting."
        exit 1
    fi

    # Navigate back to the project root for the next service
    cd "$PROJECT_ROOT_DIR" || { echo "Error: Could not navigate back to project root. Aborting."; exit 1; }
    echo "Returned to project root: $(pwd)"
    echo ""
done

echo "==================================================="
echo " All microservices built successfully! "
echo "==================================================="
echo "Maven artifacts and Docker images are ready."
echo "You can now run 'docker images' to see the built images."
echo "==================================================="

exit 0