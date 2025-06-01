package com.ltfs.cdp.reporting;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * Main Spring Boot application class for the Reporting Service.
 * This service is responsible for generating various reports related to customer,
 * offer, and campaign data within the LTFS Offer CDP system.
 *
 * It enables service discovery, allowing it to register with a discovery server
 * (e.g., Eureka) and be discoverable by other microservices.
 */
@SpringBootApplication
@EnableDiscoveryClient // Enables service registration and discovery for this microservice
public class ReportingApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It bootstraps and launches the Reporting Service.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method sets up the Spring context,
        // starts the embedded server (if configured), and initializes all beans.
        SpringApplication.run(ReportingApplication.class, args);
    }
}