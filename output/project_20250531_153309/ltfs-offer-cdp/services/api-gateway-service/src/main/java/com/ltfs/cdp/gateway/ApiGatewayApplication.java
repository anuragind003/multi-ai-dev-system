package com.ltfs.cdp.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main Spring Boot application class for the API Gateway service.
 * This class serves as the entry point for the API Gateway microservice,
 * enabling Spring Boot's auto-configuration, component scanning, and
 * configuration properties.
 *
 * The API Gateway is responsible for routing requests to various downstream
 * microservices within the LTFS Offer CDP system, providing a single entry point
 * for external clients.
 */
@SpringBootApplication
public class ApiGatewayApplication {

    /**
     * The main method that starts the Spring Boot application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method sets up the Spring context,
        // starts the embedded web server (e.g., Tomcat), and initializes all
        // components defined within the application.
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}