package com.ltfs.cdp.integration;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Integration Service.
 * This service is responsible for handling data integration aspects within the LTFS Offer CDP system,
 * including basic column-level validation and preparing data for deduplication.
 *
 * The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.integration} package, allowing it to find and register controllers,
 *         services, repositories, etc.</li>
 * </ul>
 *
 * The {@code @ComponentScan} is explicitly added here to ensure that all necessary components
 * within the project's base package structure are discovered, even if they are in sub-packages
 * not directly under 'integration' but still part of 'com.ltfs.cdp'.
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp"}) // Ensures all components within the base CDP package are scanned
public class IntegrationApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application.
        // This static method creates and runs a new SpringApplication instance,
        // performing a classpath scan, setting up a default embedded web server,
        // and registering beans.
        SpringApplication.run(IntegrationApplication.class, args);
    }
}