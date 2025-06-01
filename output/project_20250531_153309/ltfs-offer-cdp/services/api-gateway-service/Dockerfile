# Stage 1: Build the Spring Boot application
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the Maven pom.xml file to leverage Docker cache
# This step ensures that dependencies are re-downloaded only if pom.xml changes
COPY pom.xml .

# Copy the source code
COPY src ./src

# Build the Spring Boot application
# -DskipTests is used to skip running tests during the build process,
# which is common for Docker builds to speed up image creation.
RUN mvn clean install -DskipTests

# Stage 2: Create the final Docker image
# Use a smaller JRE base image for the final runtime image to reduce size
FROM openjdk:17-jre-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the built JAR file from the 'build' stage
# The JAR file is typically found in the 'target' directory after a successful Maven build.
# Adjust the JAR name if it differs (e.g., based on artifactId and version in pom.xml)
COPY --from=build /app/target/api-gateway-service-*.jar api-gateway-service.jar

# Expose the port on which the Spring Boot application will run
# Default Spring Boot port is 8080
EXPOSE 8080

# Define the entry point for the container
# This command will be executed when the container starts.
# Using 'java -jar' to run the Spring Boot application.
# -Dspring.profiles.active=docker can be added here if specific Docker profiles are needed.
ENTRYPOINT ["java", "-jar", "api-gateway-service.jar"]

# Optional: Add a health check (for production environments)
# This helps Docker and orchestrators (like Kubernetes) determine if the service is healthy.
# Adjust the path and port as per your Spring Boot Actuator configuration.
# HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
#   CMD curl -f http://localhost:8080/actuator/health || exit 1