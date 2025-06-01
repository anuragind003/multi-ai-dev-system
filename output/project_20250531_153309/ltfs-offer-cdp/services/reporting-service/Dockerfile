# Stage 1: Build the Spring Boot application
# Using a Maven image with OpenJDK 17 for building the Java application.
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven project files (pom.xml) first to leverage Docker's build cache.
# If pom.xml doesn't change, Docker can reuse the cached dependency download layer.
COPY pom.xml .

# Download project dependencies. The -B flag runs Maven in batch mode (non-interactive).
# This step ensures all dependencies are downloaded before copying source code,
# optimizing cache invalidation.
RUN mvn dependency:go-offline -B

# Copy the rest of the source code.
COPY src ./src

# Package the application into a JAR file.
# 'clean install' compiles the code and packages it.
# '-DskipTests' is used to skip running tests during the Docker build for faster image creation.
# The 'mv' command renames the generated JAR to a generic 'app.jar' for easier reference
# in the subsequent stage, regardless of the artifactId or version.
RUN mvn clean install -DskipTests && mv target/*.jar target/app.jar

# Stage 2: Create the final production image
# Using a smaller JRE-only image (OpenJDK 17 JRE slim) for the final application.
# This significantly reduces the final image size compared to a full JDK image.
FROM openjdk:17-jre-slim

# Set the working directory for the final application.
WORKDIR /app

# Copy the built JAR file from the 'build' stage into the final image.
# The 'app.jar' from the build stage is copied to the current working directory.
COPY --from=build /app/target/app.jar app.jar

# Expose the port on which the Spring Boot application is expected to run.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Define the entrypoint for the container.
# This command will be executed when the container starts.
# '-Djava.security.egd=file:/dev/./urandom' is a common JVM option for Spring Boot
# applications to improve startup time by using a non-blocking entropy source,
# which is beneficial in containerized environments.
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]