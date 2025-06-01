# Use a multi-stage build to create a smaller final image.

# --- Build Stage ---
# Use a Java Development Kit (JDK) image for building the application.
# eclipse-temurin:17-jdk-jammy provides JDK 17 on a Jammy Jellyfish (Ubuntu 22.04) base.
FROM eclipse-temurin:17-jdk-jammy AS build

# Set the working directory inside the container.
WORKDIR /app

# Copy the Maven wrapper files and the project's pom.xml.
# This allows Docker to cache the dependency download step if only source code changes.
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

# Download all project dependencies.
# Using --mount=type=cache,target=/root/.m2 caches Maven dependencies across builds,
# significantly speeding up subsequent builds if dependencies haven't changed.
# -B (batch mode) prevents interactive prompts.
RUN --mount=type=cache,target=/root/.m2 ./mvnw dependency:go-offline -B

# Copy the rest of the application source code.
COPY src src

# Build the Spring Boot application into a JAR file.
# -DskipTests skips running tests during the build, which is common for Docker builds.
RUN ./mvnw package -DskipTests

# --- Run Stage ---
# Use a Java Runtime Environment (JRE) image for running the application.
# This image is much smaller than the JDK image, resulting in a smaller final Docker image.
FROM eclipse-temurin:17-jre-jammy AS run

# Set the working directory inside the container for the running application.
WORKDIR /app

# Expose the port on which the Spring Boot application will listen.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Copy the built JAR file from the 'build' stage into the 'run' stage.
# The JAR is typically found in the 'target' directory and named after the artifactId and version.
# We rename it to 'app.jar' for simplicity.
COPY --from=build /app/target/*.jar app.jar

# Define the command to run the Spring Boot application.
# This is the default command that will be executed when the container starts.
ENTRYPOINT ["java", "-jar", "app.jar"]

# Optional: Add default command line arguments for the Spring Boot application.
# For example, to activate a specific Spring profile (e.g., 'prod').
# CMD ["--spring.profiles.active=prod"]