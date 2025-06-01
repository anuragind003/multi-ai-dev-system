#!/bin/bash

# deploy-local.sh
#
# Shell script to deploy LTFS Offer CDP services locally using Docker Compose.
# This script handles building Java projects, Docker images, and managing
# the lifecycle of the services (start, stop, rebuild, clean).

# --- Configuration ---
# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
# The return value of a pipeline is the value of the last (rightmost) command
# to exit with a non-zero status, or zero if all commands in the pipeline exit successfully.
set -euo pipefail

# Define the project root directory relative to this script.
# This assumes the script is located in a 'scripts/' subdirectory
# and the project root is one level up.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# --- Helper Functions ---

# Function to display script usage instructions.
display_usage() {
    echo "Usage: $0 {up|down|rebuild|clean}"
    echo ""
    echo "Commands:"
    echo "  up       : Builds Docker images (if not present/updated) and starts all services in detached mode."
    echo "  down     : Stops and removes all running services, networks, and default volumes."
    echo "  rebuild  : Performs a clean Maven build, rebuilds Docker images, and restarts all services."
    echo "  clean    : Stops services, removes all associated Docker resources (volumes, networks), and prunes dangling images."
    echo ""
    echo "Examples:"
    echo "  $0 up"
    echo "  $0 rebuild"
    echo "  $0 down"
    echo "  $0 clean"
    exit 1
}

# Function to check for required dependencies (Docker and Docker Compose).
check_dependencies() {
    echo "Checking for required dependencies..."
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed. Please install Docker to proceed."
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: Docker Compose is not installed. Please install Docker Compose to proceed."
        exit 1
    fi
    echo "Docker and Docker Compose found."
}

# Function to build Java projects using Maven.
# This assumes a multi-module Maven project where 'mvn clean install' at the root
# builds all service JARs required by the Dockerfiles.
build_java_projects() {
    echo "Building Java projects with Maven..."
    if [ -f "${PROJECT_ROOT}/pom.xml" ]; then
        # Navigate to the project root and execute Maven build.
        # -DskipTests is used to speed up local builds by skipping unit/integration tests.
        (cd "${PROJECT_ROOT}" && mvn clean install -DskipTests)
        if [ $? -ne 0 ]; then
            echo "Error: Maven build failed. Please check the build logs."
            exit 1
        fi
        echo "Maven build completed successfully."
    else
        echo "Warning: No pom.xml found at ${PROJECT_ROOT}. Skipping Maven build."
        echo "Ensure your Java service JARs are pre-built or handled by Dockerfiles."
    fi
}

# Function to build Docker images defined in the docker-compose file.
build_docker_images() {
    echo "Building Docker images using Docker Compose..."
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        echo "Error: Docker Compose file not found at ${DOCKER_COMPOSE_FILE}"
        exit 1
    fi
    # Execute docker-compose build.
    docker-compose -f "${DOCKER_COMPOSE_FILE}" build
    if [ $? -ne 0 ]; then
        echo "Error: Docker image build failed. Please check Dockerfile configurations and build context."
        exit 1
    fi
    echo "Docker images built successfully."
}

# Function to start services defined in the docker-compose file in detached mode.
start_services() {
    echo "Starting services using Docker Compose..."
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        echo "Error: Docker Compose file not found at ${DOCKER_COMPOSE_FILE}"
        exit 1
    fi
    # 'up -d' starts containers in detached mode.
    # '--remove-orphans' removes containers for services not defined in the compose file.
    docker-compose -f "${DOCKER_COMPOSE_FILE}" up -d --remove-orphans
    if [ $? -ne 0 ]; then
        echo "Error: Failed to start services. Check Docker logs for more details."
        exit 1
    fi
    echo "Services started successfully in detached mode."
    echo "You can view logs with: docker-compose -f ${DOCKER_COMPOSE_FILE} logs -f"
}

# Function to stop and remove services defined in the docker-compose file.
stop_services() {
    echo "Stopping services using Docker Compose..."
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        echo "Warning: Docker Compose file not found at ${DOCKER_COMPOSE_FILE}. Cannot stop services gracefully."
        return 0 # Don't exit, just warn and continue if possible.
    fi
    # 'down' stops containers and removes containers, networks, and default volumes.
    docker-compose -f "${DOCKER_COMPOSE_FILE}" down
    if [ $? -ne 0 ]; then
        echo "Error: Failed to stop services."
        exit 1
    fi
    echo "Services stopped and removed."
}

# Function to perform a full cleanup of Docker resources.
clean_all() {
    echo "Performing a full cleanup of Docker resources..."
    stop_services # First, stop any running services.

    echo "Removing all Docker volumes associated with the project..."
    # 'down -v' also removes named volumes declared in the 'volumes' section of the compose file.
    docker-compose -f "${DOCKER_COMPOSE_FILE}" down -v
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to remove all volumes. Some might be in use or require manual removal."
    fi

    echo "Pruning dangling Docker images (images not associated with any container)..."
    # 'docker image prune -f' removes all dangling images without confirmation.
    docker image prune -f
    echo "Cleanup complete."
}

# --- Main Script Logic ---

# Change directory to the project root where the docker-compose.yml file is located.
# This ensures that docker-compose commands are executed in the correct context.
cd "${PROJECT_ROOT}" || { echo "Error: Could not change to project root: ${PROJECT_ROOT}"; exit 1; }

# Check if an argument is provided. If not, display usage and exit.
if [ $# -eq 0 ]; then
    display_usage
fi

# Process the command-line argument using a case statement.
case "$1" in
    up)
        check_dependencies
        build_docker_images # Build images if they don't exist or are outdated based on Dockerfile changes.
        start_services
        ;;
    down)
        check_dependencies
        stop_services
        ;;
    rebuild)
        check_dependencies
        stop_services       # Stop existing services.
        build_java_projects # Rebuild Java JARs.
        build_docker_images # Rebuild Docker images from potentially new JARs.
        start_services      # Start services with new images.
        ;;
    clean)
        check_dependencies
        clean_all           # Perform a comprehensive cleanup.
        ;;
    *)
        display_usage       # For any other invalid argument, show usage.
        ;;
esac

echo "Deployment script finished successfully."