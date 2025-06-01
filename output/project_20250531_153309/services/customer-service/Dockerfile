# Stage 1: Build the Spring Boot application
# Uses a Java Development Kit (JDK) image to compile and package the application.
# We choose `eclipse-temurin:17-jdk-jammy` for Java 17 and a stable Debian-based distribution.
FROM eclipse-temurin:17-jdk-jammy AS build

# Set the working directory inside the container. All subsequent commands will run from here.
WORKDIR /app

# Copy the Maven project file (pom.xml) first. This allows Docker to cache this layer.
# If only source code changes, Maven dependencies won't need to be re-downloaded.
COPY pom.xml .

# Copy the source code into the container.
COPY src ./src

# Build the Spring Boot application using Maven.
# `clean package` cleans the target directory and packages the application into a JAR.
# `-DskipTests` is used to skip running tests during the build process, which is common for Docker builds
# to speed up image creation. Tests should be run in CI/CD pipelines.
RUN mvn clean package -DskipTests

# Stage 2: Create the final, lightweight runtime image
# Uses a Java Runtime Environment (JRE) image, which is much smaller than a JDK image,
# as it only contains what's necessary to run the compiled application.
# We choose `eclipse-temurin:17-jre-jammy` for Java 17.
FROM eclipse-temurin:17-jre-jammy

# Set the working directory for the runtime image.
WORKDIR /app

# Copy the built JAR file from the 'build' stage into the current stage.
# The `*.jar` wildcard is used to pick up the generated JAR file, e.g., `customer-service-0.0.1-SNAPSHOT.jar`.
# It's renamed to `app.jar` for simplicity and consistency.
COPY --from=build /app/target/*.jar app.jar

# Expose the port on which the Spring Boot application will listen.
# The default Spring Boot port is 8080.
EXPOSE 8080

# Define the command to run when the container starts.
# `java -jar app.jar` executes the Spring Boot application.
# Using the exec form `["executable", "param1", "param2"]` is preferred as it allows
# Docker to manage the process directly, avoiding issues with signal handling.
ENTRYPOINT ["java", "-jar", "app.jar"]

# Optional: Add environment variables for Spring profiles or other configurations.
# For example, to activate a 'production' profile:
# ENV SPRING_PROFILES_ACTIVE=production

# Optional: Configure JVM memory settings. This is crucial for production deployments
# to prevent the JVM from consuming too much memory in a containerized environment.
# However, it's often better to manage these via Kubernetes/Docker Compose resource limits.
# ENV JAVA_TOOL_OPTIONS="-Xmx512m -Xms256m"