#!/bin/bash

# run-local.sh
#
# Script to start and manage LTFS Offer CDP microservices locally using Docker Compose.
# This script automates the process of building Java services and orchestrating
# their startup along with dependent services (like PostgreSQL, message brokers)
# using Docker Compose.
#
# It assumes:
# 1. Docker and Docker Compose are installed and configured on the local machine.
# 2. The project follows a multi-module Maven structure where 'mvn clean install'
#    from the project root builds all necessary JARs for the microservices.
# 3. A 'docker-compose.yml' file exists at the project root, defining all services.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---

# Determine the project root directory. This script is located in 'scripts'
# relative to the project root (e.g., ltfs-offer-cdp/scripts/run-local.sh).
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Define the path to the Docker Compose file.
# Assuming 'docker-compose.yml' is located directly in the project root.
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# --- Functions ---

# Function to display usage information for the script.
display_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     Builds Java services and starts all microservices using Docker Compose (default)."
    echo "  stop      Stops and removes all microservices containers, networks, and volumes."
    echo "  restart   Stops, then rebuilds Java services, and restarts all microservices."
    echo "  build     Only builds Java services (runs 'mvn clean install -DskipTests')."
    echo "  help      Display this help message."
    echo ""
    echo "Example: $0 start"
    echo "Example: $0 stop"
}

# Function to check for necessary prerequisites (Docker, Docker Compose).
# Exits with an error if any prerequisite is not met.
check_prerequisites() {
    echo "Checking prerequisites..."
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed. Please install Docker to run services locally."
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: Docker Compose is not installed. Please install Docker Compose."
        echo "For Docker Desktop users, it's usually included. Otherwise, install it separately."
        exit 1
    fi
    echo "Docker and Docker Compose found."
}

# Function to build Java microservices using Maven.
# It navigates to the project root and runs 'mvn clean install -DskipTests'.
# '-DskipTests' is used to speed up the build for local development; remove if tests should run.
build_java_services() {
    echo "--- Building Java Microservices ---"
    echo "Navigating to project root: ${PROJECT_ROOT}"
    # Change directory to the project root. Exit if navigation fails.
    cd "${PROJECT_ROOT}" || { echo "Error: Could not navigate to project root: ${PROJECT_ROOT}"; exit 1; }

    echo "Running 'mvn clean install -DskipTests' to build all modules..."
    if mvn clean install -DskipTests; then
        echo "Java microservices built successfully."
    else
        echo "Error: Failed to build Java microservices. Please check Maven output for details."
        exit 1
    fi
    echo "-----------------------------------"
}

# Function to start services using Docker Compose.
# It first checks prerequisites, then attempts to stop any existing containers
# for a clean start, and finally brings up the services in detached mode.
start_services() {
    echo "--- Starting LTFS Offer CDP Microservices ---"
    check_prerequisites

    # Verify that the docker-compose.yml file exists.
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        echo "Error: Docker Compose file not found at ${DOCKER_COMPOSE_FILE}"
        echo "Please ensure 'docker-compose.yml' exists in the project root."
        exit 1
    fi

    echo "Stopping any existing containers for a clean start..."
    # 'docker-compose down --remove-orphans' stops and removes containers, networks,
    # and volumes. '--remove-orphans' removes containers for services not defined
    # in the compose file anymore. '|| true' prevents the script from exiting
    # if no containers are running (as 'down' would return a non-zero exit code).
    docker-compose -f "${DOCKER_COMPOSE_FILE}" down --remove-orphans || true

    echo "Starting services defined in ${DOCKER_COMPOSE_FILE}..."
    # 'docker-compose up --build -d' starts services:
    # '--build' forces a rebuild of images, useful if JARs or Dockerfiles have changed.
    # '-d' runs containers in detached mode (in the background).
    if docker-compose -f "${DOCKER_COMPOSE_FILE}" up --build -d; then
        echo "LTFS Offer CDP Microservices started successfully in detached mode."
        echo "You can check their status with: 'docker-compose -f ${DOCKER_COMPOSE_FILE} ps'"
        echo "View logs with: 'docker-compose -f ${DOCKER_COMPOSE_FILE} logs -f'"
    else
        echo "Error: Failed to start microservices using Docker Compose. Please check Docker Compose logs."
        exit 1
    fi
    echo "-------------------------------------------"
}

# Function to stop services using Docker Compose.
# It checks prerequisites and then brings down all services defined in the
# docker-compose.yml file, removing containers, networks, and volumes.
stop_services() {
    echo "--- Stopping LTFS Offer CDP Microservices ---"
    check_prerequisites

    # Verify that the docker-compose.yml file exists.
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        echo "Warning: Docker Compose file not found at ${DOCKER_COMPOSE_FILE}. Cannot stop services."
        return 0 # Don't exit, just warn and return successfully.
    fi

    echo "Stopping and removing services defined in ${DOCKER_COMPOSE_FILE}..."
    # 'docker-compose down --volumes --remove-orphans' stops and removes:
    # '--volumes' removes named volumes declared in the 'volumes' section of the Compose file.
    # '--remove-orphans' removes containers for services not defined in the compose file anymore.
    if docker-compose -f "${DOCKER_COMPOSE_FILE}" down --volumes --remove-orphans; then
        echo "LTFS Offer CDP Microservices stopped and removed successfully."
    else
        echo "Error: Failed to stop microservices using Docker Compose. Please check Docker Compose logs."
        exit 1
    fi
    echo "-------------------------------------------"
}

# --- Main Script Logic ---

# Determine the command based on the first argument.
# If no argument is provided, default to 'start'.
COMMAND=${1:-start}

# Use a case statement to handle different commands.
case "$COMMAND" in
    start)
        build_java_services # First build Java applications
        start_services      # Then start Docker Compose services
        ;;
    stop)
        stop_services       # Stop all Docker Compose services
        ;;
    restart)
        stop_services       # Stop existing services
        build_java_services # Rebuild Java applications
        start_services      # Start services again
        ;;
    build)
        build_java_services # Only build Java applications
        ;;
    help)
        display_help        # Display help message
        ;;
    *)
        # Handle unknown commands.
        echo "Error: Unknown command '$COMMAND'"
        display_help
        exit 1
        ;;
esac

echo "Script execution finished."