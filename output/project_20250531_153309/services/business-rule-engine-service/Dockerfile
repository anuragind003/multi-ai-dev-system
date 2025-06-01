#
# Build Stage
# Uses a JDK image to compile the Java application and package it into a JAR.
#
FROM eclipse-temurin:17-jdk-focal AS build

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy the Maven project files (pom.xml) first.
# This allows Docker to cache the dependencies layer if pom.xml doesn't change,
# speeding up subsequent builds.
COPY pom.xml .

# Copy the entire source code.
COPY src ./src

# Build the Spring Boot application using Maven.
# 'clean install' compiles the code, runs tests (unless skipped), and packages the JAR.
# '-DskipTests' is commonly used in Docker builds to skip running unit tests,
# as tests are typically run in a separate CI/CD stage.
RUN mvn clean install -DskipTests

#
# Production Stage
# Uses a JRE image, which is smaller than a JDK image, for the final runtime environment.
# This results in a smaller and more secure Docker image.
#
FROM eclipse-temurin:17-jre-focal AS production

# Set the working directory inside the container for the application.
WORKDIR /app

# Create a non-root user and group to run the application.
# This is a security best practice to minimize potential attack surface.
# The user 'springboot' will run the application with minimal privileges.
RUN groupadd --system springboot && useradd --system --gid springboot springboot
USER springboot

# Copy the built JAR file from the 'build' stage to the 'production' stage.
# The JAR file is expected to be named 'business-rule-engine-service-*.jar'
# and located in the 'target' directory of the build stage.
# It's renamed to 'app.jar' for simplicity within the container.
COPY --from=build /app/target/business-rule-engine-service-*.jar app.jar

# Expose the port on which the Spring Boot application will listen for incoming requests.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Define the command that will be executed when the container starts.
# 'java -jar app.jar' runs the Spring Boot application.
# '-Djava.security.egd=file:/dev/./urandom' is a common JVM argument for Spring Boot
# applications to improve startup performance by using a non-blocking source of entropy.
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]

# Optional: Add a health check. This helps container orchestrators (like Kubernetes)
# determine if the application inside the container is healthy and responsive.
# For this to work, you would typically need to expose a health endpoint (e.g., /actuator/health
# if Spring Boot Actuator is enabled) and potentially install 'curl' or 'wget' in the JRE image,
# or use a pure Java health check.
# For simplicity and to keep the image size minimal, this is commented out by default.
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD curl --fail http://localhost:8080/actuator/health || exit 1