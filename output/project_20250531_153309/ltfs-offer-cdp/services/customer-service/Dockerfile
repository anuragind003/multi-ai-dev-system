# Stage 1: Build the application
FROM maven:3.9.5-eclipse-temurin-17-jammy AS build

WORKDIR /app

# Copy the Maven wrapper and pom.xml first to leverage Docker cache
COPY pom.xml .
COPY mvnw .
COPY .mvn .mvn

# Download dependencies
RUN --mount=type=cache,target=/root/.m2 mvn dependency:go-offline -B

# Copy the source code
COPY src src

# Build the application
RUN mvn clean install -DskipTests

# Stage 2: Create the final image
FROM eclipse-temurin:17-jre-jammy AS final

# Create a non-root user and group for security best practices
RUN groupadd --system springboot && useradd --system --gid springboot springboot

# Set the working directory inside the container
WORKDIR /app

# Define an argument for the JAR file name, defaulting to a common pattern
ARG JAR_FILE=target/*.jar

# Copy the built JAR file from the build stage to the final image
COPY --from=build /app/${JAR_FILE} app.jar

# Set environment variables for Java options, including memory limits and security
ENV JAVA_OPTS="-Xms256m -Xmx512m -Djava.security.egd=file:/dev/./urandom"

# Expose the port on which the Spring Boot application will run
EXPOSE 8080

# Switch to the non-root user
USER springboot

# Define the command to run the application when the container starts
ENTRYPOINT ["java", "-jar", "app.jar"]