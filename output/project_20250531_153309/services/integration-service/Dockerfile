#
# Multi-stage Dockerfile for the Integration Service
#
# This Dockerfile builds a Spring Boot application into a lightweight Docker image.
# It uses a multi-stage approach to separate the build environment from the runtime environment,
# resulting in a smaller and more secure final image.
#

# --- Build Stage ---
# Use a Java Development Kit (JDK) image for compiling and packaging the application.
# eclipse-temurin:17-jdk-jammy provides OpenJDK 17 on a Jammy Jellyfish (Ubuntu 22.04) base.
FROM eclipse-temurin:17-jdk-jammy AS build

# Set the working directory inside the container.
WORKDIR /app

# Copy the Maven project object model (POM) file first.
# This allows Docker to cache the Maven dependencies layer, speeding up subsequent builds
# if the pom.xml hasn't changed.
COPY pom.xml .

# Copy the source code.
COPY src ./src

# Build the Spring Boot application using Maven.
# -Dmaven.test.skip=true skips running tests during the build, which is common for Docker builds
# where tests might be run in a separate CI/CD stage.
# -Dspring-boot.repackage.skip=true is not needed as we want the executable JAR.
# The `package` goal will create the executable JAR in the `target/` directory.
RUN mvn clean package -Dmaven.test.skip=true

# --- Run Stage ---
# Use a Java Runtime Environment (JRE) image for running the application.
# This image is significantly smaller than the JDK image, reducing the final image size.
FROM eclipse-temurin:17-jre-jammy AS run

# Set the working directory inside the container.
WORKDIR /app

# Copy the executable JAR file from the 'build' stage to the 'run' stage.
# The JAR is typically named `integration-service-*.jar` based on the Maven artifactId.
# We use a wildcard to account for version numbers in the JAR name.
COPY --from=build /app/target/integration-service-*.jar integration-service.jar

# Expose the port on which the Spring Boot application will listen.
# The default port for Spring Boot applications is 8080.
EXPOSE 8080

# Define the entry point for the container.
# This command will execute the Spring Boot application when the container starts.
# `java -jar` runs the packaged JAR file.
# `-Dspring.profiles.active=production` sets the active Spring profile to 'production'.
# This allows environment-specific configurations to be loaded.
ENTRYPOINT ["java", "-jar", "integration-service.jar"]