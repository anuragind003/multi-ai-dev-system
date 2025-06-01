package com.ltfs.cdp.campaign;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Campaign Service.
 * This class serves as the entry point for the microservice.
 *
 * The `@SpringBootApplication` annotation is a convenience annotation that
 * adds:
 * - `@Configuration`: Tags the class as a source of bean definitions for the
 *   application context.
 * - `@EnableAutoConfiguration`: Tells Spring Boot to start adding beans based on
 *   classpath settings, other beans, and various property settings.
 * - `@ComponentScan`: Tells Spring to look for other components, services, and
 *   configurations in the `com.ltfs.cdp.campaign` package, allowing it to
 *   discover and register beans.
 *
 * This service is part of the LTFS Offer CDP project, responsible for managing
 * campaign-related data and logic, including offer finalization and deduplication
 * processes as per the functional requirements.
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.campaign"}) // Explicitly define base package for component scanning
public class CampaignApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application.
        // This method creates and refreshes an appropriate ApplicationContext,
        // and then calls the run method on any ApplicationRunner or CommandLineRunner beans.
        SpringApplication.run(CampaignApplication.class, args);
    }
}