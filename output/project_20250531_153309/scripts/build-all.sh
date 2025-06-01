#!/bin/bash

# scripts/build-all.sh
#
# Purpose: Shell script to build all microservices for the LTFS Offer CDP project
#          using Maven. This script assumes a multi-module Maven project structure
#          where 'mvn clean install' executed from the project root will build all
#          sub-modules (microservices).
#
# Project Context: LTFS Offer CDP - A new system designed to eliminate manual processes,
#                  enable faster processing, and improve the management of customer,
#                  campaign, and various offer data.
# Technology Stack: Java + Spring Boot, PostgreSQL, Microservices Architecture.
#
# Usage:
#   Navigate to the 'scripts' directory or run from project root:
#   ./scripts/build-all.sh
#
# Error Handling:
# - Exits immediately if any command fails (`set -e`).
# - Checks for Maven installation.
# - Provides clear success/failure messages with colored output.
#
# Dependencies:
# - Maven must be installed and accessible in the system's PATH.
#

# Exit immediately if a command exits with a non-zero status.
set -e

# Define colors for better output in the terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN}  LTFS Offer CDP - Building All Microservices        ${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo ""

# --- Step 1: Check for Maven installation ---
echo -e "${YELLOW}Checking for Maven installation...${NC}"
if ! command -v mvn &> /dev/null
then
    echo -e "${RED}Error: Maven is not installed or not found in your PATH.${NC}"
    echo -e "${RED}Please install Maven and ensure it's accessible before running this script.${NC}"
    exit 1
fi
echo -e "${GREEN}Maven found.${NC}"
echo ""

# --- Step 2: Navigate to the project root directory ---
# This script is located in 'scripts/', so the project root is one level up.
# `dirname "$0"` gets the directory where the script itself resides.
# `..` then navigates up to the parent directory, which is assumed to be the project root.
PROJECT_ROOT="$(dirname "$0")/.."
echo -e "${YELLOW}Navigating to project root: ${PROJECT_ROOT}${NC}"
cd "$PROJECT_ROOT"

# Check if the navigation was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Could not navigate to project root: $PROJECT_ROOT${NC}"
    echo -e "${RED}Please ensure the script is located within the 'scripts' directory inside your project.${NC}"
    exit 1
fi
echo -e "${GREEN}Successfully changed directory to project root.${NC}"
echo ""

# --- Step 3: Execute Maven build (clean install) ---
echo -e "${GREEN}Starting Maven build (clean install) for all microservices...${NC}"
echo -e "${YELLOW}This process may take a few minutes depending on dependencies and project size.${NC}"
echo -e "${YELLOW}Output will be streamed below:${NC}"
echo ""

# Execute Maven clean install in batch mode.
# -B or --batch-mode: Runs Maven in non-interactive (batch) mode, which is ideal for scripts.
#                     It suppresses prompts and uses default values.
# `clean`: Cleans the target directory, removing previously compiled classes and artifacts.
# `install`: Compiles the source code, runs tests, packages the compiled code into JARs/WARs,
#            and installs the artifacts into the local Maven repository. This is crucial
#            for multi-module projects where one module might depend on another.
mvn clean install -B

# --- Step 4: Check the exit status of the Maven command and provide final feedback ---
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=====================================================${NC}"
    echo -e "${GREEN}  All Microservices Built Successfully!              ${NC}"
    echo -e "${GREEN}  Artifacts are installed in your local Maven repo.  ${NC}"
    echo -e "${GREEN}=====================================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=====================================================${NC}"
    echo -e "${RED}  Error: Failed to build one or more microservices.  ${NC}"
    echo -e "${RED}  Please review the Maven output above for details on the failure. ${NC}"
    echo -e "${RED}=====================================================${NC}"
    exit 1
fi