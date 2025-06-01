package com.ltfs.cdp.campaign;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Campaign Service.
 * This class serves as the entry point for the microservice,
 * enabling Spring Boot's auto-configuration, component scanning,
 * and configuration capabilities.
 *
 * The Campaign Service is responsible for managing campaign-related data
 * and logic within the LTFS Offer CDP system.
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.campaign"}) // Explicitly define base packages for component scanning
public class CampaignApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application.
        // This static method creates and runs a new Spring application from the specified source.
        SpringApplication.run(CampaignApplication.class, args);
    }
}