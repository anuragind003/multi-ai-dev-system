package com.ltfs.cdp.admin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Admin Portal Service.
 * This service provides functionalities for managing customer, campaign, and offer data
 * within the LTFS Offer CDP (Customer Data Platform).
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.admin} package, allowing it to find and register controllers, services,
 *         repositories, etc.</li>
 * </ul>
 *
 * <p>This application is part of a microservices architecture and will handle administrative tasks
 * related to the CDP system, such as managing user access, system configurations, and potentially
 * monitoring data ingestion processes.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.admin") // Explicitly define base package for component scanning
public class AdminPortalApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, loading all beans and starting the embedded web server (if applicable).
        SpringApplication.run(AdminPortalApplication.class, args);
    }
}