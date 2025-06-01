package com.ltfs.cdp.admin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Admin Portal Service.
 * This class serves as the entry point for the Admin Portal microservice,
 * enabling administrative functionalities for the LTFS Offer CDP system.
 *
 * The @SpringBootApplication annotation is a convenience annotation that adds:
 * - @Configuration: Tags the class as a source of bean definitions for the application context.
 * - @EnableAutoConfiguration: Tells Spring Boot to start adding beans based on classpath settings,
 *   other beans, and various property settings.
 * - @ComponentScan: Tells Spring to look for other components, configurations, and services
 *   in the 'com.ltfs.cdp.admin' package, allowing it to discover and register beans.
 *
 * The Admin Portal is a critical component for managing customer, campaign, and offer data,
 * supporting operations like data validation, deduplication configuration, and system monitoring.
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.admin", "com.ltfs.cdp.common"}) // Scan current package and common utilities
public class AdminPortalApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the Admin Portal service.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes a new
        // ApplicationContext and starts the embedded Tomcat server (if web dependencies are present).
        SpringApplication.run(AdminPortalApplication.class, args);
    }
}