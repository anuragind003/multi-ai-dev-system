# --- Build Stage ---
# Use a Maven image with OpenJDK 17 for building the Spring Boot application.
# This stage compiles the Java code and packages it into a JAR file.
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven project file (pom.xml) first.
# This allows Docker to cache the dependency download step. If only source code changes,
# this step won't re-run, speeding up subsequent builds.
COPY pom.xml .

# Download project dependencies.
# 'dependency:go-offline' downloads all project dependencies to the local Maven repository,
# ensuring they are available for the build even without an internet connection later.
RUN mvn dependency:go-offline

# Copy the rest of the source code into the container.
COPY src ./src

# Build the Spring Boot application.
# 'clean install' compiles the code, runs tests (skipped here with -DskipTests for faster builds),
# and packages the application into a JAR file in the 'target' directory.
# '-DskipTests' is used to skip running unit tests during the Docker build process,
# as tests should ideally be run in a separate CI/CD pipeline step.
RUN mvn clean install -DskipTests

# --- Run Stage ---
# Use a smaller JRE (Java Runtime Environment) base image for the final production image.
# This significantly reduces the final image size compared to using the full JDK image.
FROM eclipse-temurin:17-jre-focal

# Set the working directory inside the container for the running application.
WORKDIR /app

# Copy the built JAR file from the 'build' stage into the current stage.
# The JAR file is typically named 'api-gateway-service.jar' or similar, based on pom.xml's artifactId.
# We use a wildcard to ensure it picks up the correct JAR name.
COPY --from=build /app/target/*.jar api-gateway-service.jar

# Expose the port on which the Spring Boot application will listen.
# The default port for Spring Boot applications is 8080.
EXPOSE 8080

# Define the entry point for the container.
# This command will be executed when the container starts.
# '-Djava.security.egd=file:/dev/./urandom' is a common JVM argument for Spring Boot applications
# running in containers. It helps to speed up startup time by using /dev/./urandom
# as a source of entropy, which is faster than /dev/random.
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "api-gateway-service.jar"]