#!/bin/bash
#
# scripts/run-tests.sh
#
# Script to execute all unit and integration tests for the LTFS Offer CDP project.
# This project uses Java + Spring Boot with Maven.
#
# Assumes a multi-module Maven project structure where 'mvn clean install'
# from the root directory will build and test all submodules.
#

# --- Configuration and Error Handling ---

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# The return value of a pipeline is the status of the last command to exit with a non-zero status,
# or zero if all commands in the pipeline exit successfully.
set -o pipefail

# Define the Maven command.
MAVEN_CMD="mvn"

# --- Functions ---

# Function to check if a command exists in the system's PATH.
# Arguments:
#   $1 - The command name to check.
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run Maven tests.
# This function navigates to the project root and executes the Maven 'clean install' goal.
# 'clean' removes previous build artifacts.
# 'install' compiles the source code, runs unit tests, packages the compiled code,
# and then runs integration tests (if configured in the project's pom.xml using plugins like Maven Failsafe Plugin).
# The '-B' flag enables batch mode, which is useful for non-interactive environments like CI/CD.
# '-Dmaven.test.failure.ignore=false' ensures that the build fails if any tests fail.
# '-DskipTests=false' explicitly ensures that tests are run (overriding any default skips).
run_maven_tests() {
    echo "-------------------------------------------------------------------"
    echo "Starting Maven build and test execution..."
    echo "This will run unit and integration tests as configured in the project's POM files."
    echo "-------------------------------------------------------------------"

    # Execute Maven command.
    if ! "$MAVEN_CMD" clean install -B -Dmaven.test.failure.ignore=false -DskipTests=false; then
        echo "-------------------------------------------------------------------"
        echo "ERROR: Maven tests failed!"
        echo "Please review the logs above for details on test failures."
        echo "-------------------------------------------------------------------"
        exit 1 # Exit with a non-zero status to indicate failure
    fi

    echo "-------------------------------------------------------------------"
    echo "Maven build and tests completed successfully."
    echo "-------------------------------------------------------------------"
}

# --- Main Execution ---

echo "==================================================================="
echo "LTFS Offer CDP - Test Execution Script"
echo "==================================================================="

# 1. Check for Maven installation.
if ! command_exists "$MAVEN_CMD"; then
    echo "ERROR: Maven ('$MAVEN_CMD') command not found."
    echo "Please ensure Maven is installed and available in your system's PATH."
    exit 1
fi
echo "Maven found: $(command -v "$MAVEN_CMD")"

# 2. Check for Java Development Kit (JDK) installation.
# Maven requires a JDK to compile and run Java applications.
if ! command_exists "java"; then
    echo "ERROR: Java ('java') command not found."
    echo "Please ensure a Java Development Kit (JDK) is installed and available in your system's PATH."
    exit 1
fi
echo "Java found: $(command -v "java")"
echo "Java Version: $("java" -version 2>&1 | head -n 1)" # Display the Java version

# 3. Determine the project root directory.
# This script is located at 'scripts/run-tests.sh'.
# The project root is one directory level up from the script's location.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Verify that a pom.xml exists in the determined project root,
# which is a strong indicator of a Maven project.
if [ ! -f "$PROJECT_ROOT/pom.xml" ]; then
    echo "ERROR: pom.xml not found in '$PROJECT_ROOT'."
    echo "This script expects to be run from the 'scripts' directory within a Maven project structure."
    echo "Please ensure the script is placed correctly or run it from the project root."
    exit 1
fi

echo "Navigating to project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# 4. Execute the Maven tests.
run_maven_tests

echo "==================================================================="
echo "All tests completed successfully for LTFS Offer CDP."
echo "==================================================================="

# Exit with a zero status to indicate success.
exit 0