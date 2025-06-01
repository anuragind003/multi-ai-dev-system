# Use a lightweight Java Runtime Environment (JRE) as the base image for the final stage.
# eclipse-temurin:17-jre-jammy provides a JRE based on Ubuntu Jammy, which is suitable for production.
FROM eclipse-temurin:17-jre-jammy

# Set the working directory inside the container.
# All subsequent commands will be executed relative to this directory.
WORKDIR /app

# Define an argument for the JAR file name.
# This allows the JAR file name to be passed during the build process (e.g., using --build-arg).
ARG JAR_FILE=target/reporting-service.jar

# Copy the JAR file from the host machine into the container's /app directory.
# The JAR_FILE argument specifies the path to the compiled Spring Boot application JAR.
COPY ${JAR_FILE} app.jar

# Expose the port that the Spring Boot application will listen on.
# By default, Spring Boot applications run on port 8080.
EXPOSE 8080

# Define the entrypoint for the container.
# This command will be executed when the container starts.
# `java -jar app.jar` runs the Spring Boot application.
# `-Djava.security.egd=file:/dev/./urandom` is a common recommendation for Spring Boot
# applications to speed up startup time by using a non-blocking entropy source.
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]