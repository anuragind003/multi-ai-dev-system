# Use an official OpenJDK runtime as a parent image for building
FROM maven:3.8.5-openjdk-17 AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the pom.xml and download dependencies to leverage Docker cache
# This step ensures that if only source code changes, dependencies are not re-downloaded
COPY pom.xml .
RUN mvn dependency:go-offline

# Copy the entire source code
COPY src ./src

# Package the application into a JAR file
# The -DskipTests flag is used to skip running tests during the build process,
# which is common for Docker builds to speed up image creation.
RUN mvn clean install -DskipTests

# Use a smaller base image for the final runtime stage
# This helps in reducing the final Docker image size, as it only contains the JRE
# and not the full JDK or Maven.
FROM openjdk:17-jre-slim

# Set the working directory for the final image
WORKDIR /app

# Copy the built JAR file from the 'build' stage to the current stage
# The name of the JAR file is typically derived from the artifactId in pom.xml
# and the version. Assuming the artifactId is 'business-rule-engine-service'.
COPY --from=build /app/target/business-rule-engine-service-*.jar app.jar

# Expose the port on which the Spring Boot application will run
# Default Spring Boot port is 8080
EXPOSE 8080

# Define the entry point for the container
# This command will execute when the container starts.
# -Dspring.profiles.active=prod: Activates the 'prod' Spring profile,
#   which is good practice for production deployments to load production-specific configurations.
# -Xmx256m -Xms256m: Sets initial and maximum heap size for the JVM.
#   Adjust these values based on the service's memory requirements.
#   Using fixed values helps in predictable memory usage within containers.
ENTRYPOINT ["java", "-Dspring.profiles.active=prod", "-Xmx256m", "-Xms256m", "-jar", "app.jar"]