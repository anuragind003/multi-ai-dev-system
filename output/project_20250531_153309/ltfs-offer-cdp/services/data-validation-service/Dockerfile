# Stage 1: Build the Spring Boot application
# Using Maven 3.8.6 with OpenJDK 17 as the build environment.
FROM maven:3.8.6-openjdk-17 AS build

# Set the working directory inside the build container.
WORKDIR /app

# Copy the Maven project files (pom.xml, mvnw, .mvn directory) first.
# This allows Docker to cache these layers if only source code changes, speeding up builds.
COPY pom.xml .
COPY mvnw .
COPY .mvn .mvn/

# Download project dependencies.
# Using a cache mount for Maven's local repository to speed up subsequent builds.
# The -B (batch mode) flag prevents interactive prompts.
RUN --mount=type=cache,target=/root/.m2 mvn dependency:go-offline -B

# Copy the entire source code into the build container.
COPY src src/

# Build the Spring Boot application.
# 'clean install' compiles, packages, and installs the artifact.
# '-DskipTests' skips running tests during the build, which is common for Docker builds.
RUN mvn clean install -DskipTests

# Stage 2: Create the final, lightweight Docker image for the application runtime.
# Using OpenJDK 17 JRE (Java Runtime Environment) slim image for a smaller footprint.
FROM openjdk:17-jre-slim

# Set the working directory inside the final container.
WORKDIR /app

# Copy the executable JAR file from the build stage to the current stage.
# The JAR is typically found in the 'target' directory of the Maven build.
# We rename it to 'app.jar' for simplicity and consistency.
COPY --from=build /app/target/*.jar app.jar

# Expose the port on which the Spring Boot application will listen.
# Default Spring Boot port is 8080.
EXPOSE 8080

# Define environment variables for the application.
# SPRING_PROFILES_ACTIVE sets the active Spring profile (e.g., 'production', 'dev').
# JAVA_OPTS provides JVM arguments for memory allocation, garbage collection, etc.
# These values should be tuned based on actual application memory requirements.
# -Djava.security.egd=file:/dev/./urandom is a common optimization for Spring Boot startup.
ENV SPRING_PROFILES_ACTIVE=production
ENV JAVA_OPTS="-Xms256m -Xmx512m -XX:MaxMetaspaceSize=256m -Djava.security.egd=file:/dev/./urandom"

# Install curl for health checks. 'jre-slim' images are minimal and don't include it by default.
# --no-install-recommends prevents installation of recommended but not strictly necessary packages.
# rm -rf /var/lib/apt/lists/* cleans up apt cache to keep the image size small.
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Define the command to run the Spring Boot application when the container starts.
# 'java -jar app.jar' executes the packaged Spring Boot application.
# The JAVA_OPTS environment variable is automatically picked up by the 'java' command.
ENTRYPOINT ["java", "-jar", "app.jar"]

# Define a health check for the container.
# This helps orchestrators (like Kubernetes) determine if the application is healthy.
# It checks the Spring Boot Actuator health endpoint.
HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

# Add labels for metadata (optional but good practice for image management)
LABEL maintainer="LTFS Offer CDP Team"
LABEL description="Dockerfile for Data Validation Service"
LABEL version="1.0.0"