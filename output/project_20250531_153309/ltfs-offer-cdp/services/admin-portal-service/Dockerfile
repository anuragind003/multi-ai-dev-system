#
# Build Stage
#
FROM eclipse-temurin:17-jdk-jammy AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the Maven project files
# Copy pom.xml first to leverage Docker layer caching for dependencies
COPY pom.xml .
# Copy Maven wrapper scripts if they exist
COPY mvnw .
COPY .mvn .mvn/

# Download project dependencies to cache them
# This step will only re-run if pom.xml changes
# Using --mount=type=cache for Maven local repository caching to speed up subsequent builds
RUN --mount=type=cache,target=/root/.m2/repository mvn dependency:go-offline -B

# Copy the rest of the source code
COPY src src/

# Build the application JAR
# -DskipTests: Skips running tests to speed up the build process
# -Dmaven.compiler.source=17 -Dmaven.compiler.target=17: Explicitly set Java version for compilation
RUN mvn clean install -DskipTests -Dmaven.compiler.source=17 -Dmaven.compiler.target=17

#
# Run Stage
#
FROM eclipse-temurin:17-jre-jammy

# Set the working directory inside the container
WORKDIR /app

# Create a non-root user and group for security best practices
# This user will be used to run the application, reducing potential attack surface
RUN groupadd --system springboot && useradd --system --gid springboot springboot

# Define an argument for the JAR file name.
# This assumes the JAR is named based on the Maven artifactId (e.g., admin-portal-service-0.0.1-SNAPSHOT.jar)
# We use a wildcard to pick up the generated JAR from the 'target' directory.
ARG JAR_FILE=target/*.jar

# Copy the built JAR file from the 'build' stage into the 'run' stage
# Rename it to 'app.jar' for simplicity and consistency within the container
COPY --from=build /app/${JAR_FILE} app.jar

# Set ownership of the application JAR to the non-root user
# This ensures the 'springboot' user has the necessary permissions to read and execute the JAR
RUN chown springboot:springboot app.jar

# Switch to the non-root user for running the application
# All subsequent commands will be executed as this user
USER springboot

# Expose the port on which the Spring Boot application will listen
# This informs Docker that the container listens on the specified network port at runtime
# Default Spring Boot port is 8080
EXPOSE 8080

# Define the command to run the application
# Using the 'exec' form of ENTRYPOINT is recommended for proper signal handling (e.g., graceful shutdown)
# This ensures that signals like SIGTERM are correctly propagated to the Java process
ENTRYPOINT ["java", "-jar", "app.jar"]