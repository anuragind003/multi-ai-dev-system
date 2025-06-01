# Stage 1: Build the Spring Boot application
# Uses a Maven image with OpenJDK 17 to build the Java application.
FROM maven:3.8.6-openjdk-17 AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven project file (pom.xml) first.
# This allows Docker to cache this layer. If only source code changes,
# Maven dependencies won't be re-downloaded.
COPY pom.xml .

# Copy the entire source code of the application.
COPY src ./src

# Build the Spring Boot application.
# 'clean package' compiles the code, runs tests (unless skipped), and packages it into a JAR.
# '-DskipTests' is often used in Docker builds to speed up the process, assuming tests
# are run in a separate CI/CD stage.
RUN mvn clean package -DskipTests

# Stage 2: Create the final lightweight runtime image
# Uses a smaller JRE-only OpenJDK 17 image for the final application.
# This significantly reduces the final image size compared to the build image.
FROM openjdk:17-jre-slim

# Set the working directory for the application inside the container.
WORKDIR /app

# Copy the built JAR file from the 'build' stage to the current stage.
# The JAR is typically found in the 'target/' directory after a Maven build.
# We rename it to 'campaign-service.jar' for consistency and easier reference.
COPY --from=build /app/target/*.jar campaign-service.jar

# Expose the port that the Spring Boot application listens on.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Define environment variables for Spring Boot configuration.
# These can be overridden at runtime using 'docker run -e'.
# SPRING_PROFILES_ACTIVE: Sets the active Spring profile (e.g., 'prod', 'dev').
# JAVA_OPTS: Provides JVM arguments, such as memory allocation.
ENV SPRING_PROFILES_ACTIVE=prod
ENV JAVA_OPTS="-Xms256m -Xmx512m"

# Define the entry point for the container.
# This command will be executed when the container starts.
# The 'exec' form (JSON array) is preferred as it allows Docker to properly
# manage the process and send signals (e.g., SIGTERM for graceful shutdown).
ENTRYPOINT ["java", "-jar", "campaign-service.jar"]