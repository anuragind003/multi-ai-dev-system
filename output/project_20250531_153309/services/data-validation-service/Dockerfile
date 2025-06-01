# Stage 1: Build the Spring Boot application
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the Maven project files (pom.xml first to leverage Docker cache)
COPY pom.xml .

# Copy the source code
COPY src ./src

# Build the application, skipping tests for faster build in Docker
# The resulting JAR will be in target/
RUN mvn clean install -DskipTests

# Stage 2: Create the final Docker image for runtime
# Use a smaller JRE-only image for the runtime environment
FROM eclipse-temurin:17-jre-focal

# Set the working directory inside the container
WORKDIR /app

# Create a non-root user and group for security best practices
RUN groupadd --system springboot && useradd --system --gid springboot springboot
USER springboot

# Copy the built JAR file from the build stage to the current stage
# Using '*.jar' to be flexible with version numbers in the JAR name
COPY --from=build /app/target/*.jar app.jar

# Expose the port on which the Spring Boot application will run
EXPOSE 8080

# Define the entrypoint to run the Spring Boot application
# Add JVM memory settings for production-grade deployment
ENTRYPOINT ["java", "-Xms256m", "-Xmx512m", "-jar", "app.jar"]

# Optional: Add a health check (requires Spring Boot Actuator dependency)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl --fail http://localhost:8080/actuator/health || exit 1