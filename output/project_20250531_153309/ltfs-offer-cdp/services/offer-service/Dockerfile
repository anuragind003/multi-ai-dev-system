#
# Build Stage: Compiles the Spring Boot application
# Uses a Maven image with OpenJDK 17 to build the project.
#
FROM maven:3.8.5-openjdk-17 AS builder

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven project definition file (pom.xml) first.
# This allows Docker to cache this layer. If pom.xml doesn't change,
# subsequent builds will use the cached layer, speeding up the process.
COPY pom.xml .

# Copy the entire source code of the Spring Boot application.
COPY src ./src

# Build the Spring Boot application using Maven.
# 'clean install' cleans the target directory and builds the project,
# installing the artifact into the local Maven repository.
# '-DskipTests' skips running unit and integration tests during the build
# to speed up image creation. Tests should be run in CI/CD pipelines.
RUN mvn clean install -DskipTests

#
# Run Stage: Creates a lightweight image to run the compiled application
# Uses a slim JRE (Java Runtime Environment) image for a smaller final image size.
#
FROM openjdk:17-jre-slim

# Set the working directory inside the container for the running application.
WORKDIR /app

# Copy the built JAR file from the 'builder' stage into the current stage.
# The JAR file is typically found in the 'target' directory after a Maven build.
# Using '*.jar' handles cases where the JAR name includes a version number
# (e.g., 'offer-service-1.0.0-SNAPSHOT.jar').
# The JAR is renamed to 'app.jar' for simplicity and consistency.
COPY --from=builder /app/target/*.jar app.jar

# Expose the port on which the Spring Boot application will listen.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Set an environment variable to activate a specific Spring profile.
# 'prod' is commonly used for production configurations, allowing different
# settings (e.g., database connections, logging levels) based on the environment.
ENV SPRING_PROFILES_ACTIVE=prod

# Create a non-root user and group for enhanced security.
# Running applications as non-root users is a best practice to mitigate
# potential security vulnerabilities.
RUN addgroup --system spring && adduser --system --ingroup spring spring
USER spring

# Define the command that will be executed when the container starts.
# 'java -Djava.security.egd=file:/dev/./urandom' is used to improve
# startup time by providing a non-blocking source of entropy for
# cryptographic operations, especially in containerized environments.
# '-jar app.jar' specifies the JAR file to execute.
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]