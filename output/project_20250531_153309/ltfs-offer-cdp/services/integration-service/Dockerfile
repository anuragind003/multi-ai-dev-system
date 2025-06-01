# Use a multi-stage build to create a smaller, more secure production image.

# --- Build Stage ---
# Use a Java Development Kit (JDK) image for compiling the Spring Boot application.
# eclipse-temurin provides OpenJDK builds. 17 is a common LTS version for Spring Boot.
FROM eclipse-temurin:17-jdk-jammy as build

# Set the working directory inside the container.
WORKDIR /app

# Copy Maven wrapper files and pom.xml first to leverage Docker layer caching.
# This allows Maven dependencies to be downloaded only when pom.xml changes.
COPY .mvn/ .mvn
COPY mvnw pom.xml ./

# Download project dependencies. This step is cached if pom.xml doesn't change.
# -Dmaven.wagon.http.ssl.insecure=true might be needed in some corporate proxies,
# but generally not recommended for production. Omitting for a standard build.
RUN ./mvnw dependency:go-offline

# Copy the source code into the container.
COPY src ./src

# Build the Spring Boot application.
# clean: Cleans the target directory.
# install: Compiles, tests (by default), and packages the application into a JAR.
# -DskipTests: Skips running tests during the build. This is common for Docker builds
# where tests might be run in a separate CI/CD stage or locally.
RUN ./mvnw clean install -DskipTests

# --- Runtime Stage ---
# Use a Java Runtime Environment (JRE) image, which is smaller than a JDK image,
# as it only needs to run the application, not compile it.
FROM eclipse-temurin:17-jre-jammy

# Set the working directory for the runtime image.
WORKDIR /app

# Copy the built JAR file from the 'build' stage to the current stage.
# The JAR file is typically found in the 'target' directory of the build stage.
# We assume the JAR name will be 'integration-service.jar' based on the service name,
# or a generic '*.jar' if the exact name is not known or might vary.
# Using 'app.jar' as a consistent name inside the container.
COPY --from=build /app/target/integration-service-*.jar app.jar

# Expose the port on which the Spring Boot application will run.
# Default Spring Boot port is 8080.
EXPOSE 8080

# Define the command to run the application when the container starts.
# This uses the 'exec' form of ENTRYPOINT, which is preferred as it allows
# the application to receive signals (like SIGTERM) properly.
# -jar: Specifies that the JAR file should be executed.
# app.jar: The name of the JAR file copied into the container.
ENTRYPOINT ["java", "-jar", "app.jar"]