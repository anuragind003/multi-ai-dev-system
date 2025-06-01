# Use a multi-stage build to create a smaller final image

# --- Build Stage ---
# Use a Java 17 JDK image for building the application
FROM eclipse-temurin:17-jdk-focal AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the Maven project file (pom.xml) first to leverage Docker cache
# This step is crucial for faster builds if only source code changes
COPY pom.xml .

# Copy the entire source code
COPY src ./src

# Build the Spring Boot application using Maven
# -Dmaven.test.skip=true skips running tests during the build
# -Dspring-boot.repackage.skip=true prevents Spring Boot from repackaging the JAR
# This is useful if you want to control the final JAR name or structure
# However, for a standard Spring Boot app, we usually want the repackaged JAR.
# So, we'll just build the package.
RUN mvn clean package -DskipTests

# --- Run Stage ---
# Use a smaller JRE image for the final runtime image
FROM eclipse-temurin:17-jre-focal

# Set the working directory inside the container
WORKDIR /app

# Copy the built JAR file from the 'build' stage
# The JAR file is typically found in the 'target' directory after a successful Maven build
# The name of the JAR file will be `campaign-service-*.jar` based on the project's artifactId and version
# We use a wildcard to ensure it picks up the correct versioned JAR.
COPY --from=build /app/target/campaign-service-*.jar app.jar

# Expose the port on which the Spring Boot application will run
# Default Spring Boot port is 8080
EXPOSE 8080

# Define the entry point for the container
# This command will be executed when the container starts
# It runs the Spring Boot application using java -jar
# You can pass Spring profiles or other JVM arguments here if needed,
# e.g., -Dspring.profiles.active=production
ENTRYPOINT ["java", "-jar", "app.jar"]

# Optional: Add metadata for the image
LABEL maintainer="LTFS Offer CDP Team"
LABEL description="Dockerfile for LTFS Offer CDP Campaign Service"
LABEL version="1.0.0"