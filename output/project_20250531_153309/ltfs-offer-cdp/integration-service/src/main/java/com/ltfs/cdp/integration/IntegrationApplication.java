package com.ltfs.cdp.integration;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Integration Service.
 * This service is responsible for handling data integration from Offermart to the CDP System,
 * performing validations, and initiating deduplication processes.
 *
 * The @SpringBootApplication annotation is a convenience annotation that adds:
 * - @Configuration: Tags the class as a source of bean definitions for the application context.
 * - @EnableAutoConfiguration: Tells Spring Boot to start adding beans based on classpath settings,
 *   other beans, and various property settings. For example, if spring-webmvc is on the classpath,
 *   this annotation flags the application as a web application and activates key behaviors
 *   such as setting up a DispatcherServlet.
 * - @ComponentScan: Tells Spring to look for other components, configurations, and services
 *   in the `com.ltfs.cdp.integration` package, allowing it to find and register controllers,
 *   services, repositories, etc.
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.integration"}) // Explicitly define base package for component scanning
public class IntegrationApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes the Spring application context,
        // performs classpath scanning, and starts the embedded web server (if applicable).
        SpringApplication.run(IntegrationApplication.class, args);
    }
}