#
# Build stage
#
# Uses a Maven image with OpenJDK 17 to build the Spring Boot application.
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven POM file first. This allows Docker to cache the dependency download step.
# If pom.xml doesn't change, subsequent builds will reuse the cached layer.
COPY pom.xml .

# Download project dependencies.
# 'dependency:go-offline' downloads all project dependencies to the local Maven repository.
# This ensures that the 'mvn clean install' step doesn't need to download dependencies again,
# making the build faster and more reliable, especially in environments with limited internet access.
RUN mvn dependency:go-offline

# Copy the entire source code into the container.
COPY src ./src

# Build the Spring Boot application.
# 'clean install': Cleans the target directory and builds the project, installing the artifact into the local Maven repository.
# '-DskipTests': Skips running tests during the build process to speed up image creation.
# '--batch-mode': Runs Maven in non-interactive (batch) mode, suitable for CI/CD environments.
RUN mvn clean install -DskipTests --batch-mode

#
# Run stage
#
# Uses a smaller JRE-only image for the final application image.
# This significantly reduces the final image size compared to a full JDK image,
# improving deployment speed and reducing attack surface.
FROM openjdk:17-jre-slim

# Set the working directory inside the container for the running application.
WORKDIR /app

# Define a non-root user and group for security best practices.
# Running applications as non-root users mitigates potential security vulnerabilities.
RUN groupadd --system springboot && useradd --system --gid springboot springboot
USER springboot

# Define an argument for the JAR file name.
# This allows overriding the JAR file pattern during the build command if needed.
# The wildcard `*.jar` is used to match the generated JAR file, which typically includes the version.
ARG JAR_FILE=target/admin-portal-service-*.jar

# Copy the built JAR file from the 'build' stage into the current 'run' stage.
# The JAR file is located in the '/app/target' directory of the build stage.
COPY --from=build /app/${JAR_FILE} app.jar

# Expose the port that the Spring Boot application listens on.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Define an environment variable for JVM options.
# This allows passing additional JVM arguments (e.g., memory allocation, garbage collection settings)
# to the Java process at runtime without modifying the Dockerfile.
ENV JAVA_OPTS=""

# Define the entry point for the container.
# This command will be executed when the container starts.
# It runs the Spring Boot application using 'java -jar'.
# The '$JAVA_OPTS' variable is expanded at runtime, allowing dynamic JVM configuration.
ENTRYPOINT ["java", "$JAVA_OPTS", "-jar", "app.jar"]

# Optional: Add a health check.
# Uncomment and configure this section to enable Docker's built-in health checks.
# This helps orchestrators (like Kubernetes) determine if the application is healthy.
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#   CMD curl --fail http://localhost:8080/actuator/health || exit 1