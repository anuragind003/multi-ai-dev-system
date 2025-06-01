package com.ltfs.cdp.bre;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Business Rule Engine Service.
 * This service is responsible for applying various business rules,
 * including data validation, deduplication logic, and offer finalization rules,
 * as part of the LTFS Offer CDP (Customer Data Platform) project.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.bre} package, allowing it to find and register controllers, services,
 *         repositories, etc.</li>
 * </ul>
 *
 * <p>The {@code @ComponentScan} is explicitly used here to ensure that all necessary components
 * within the defined package structure are discovered and managed by Spring.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.bre")
public class BusinessRuleEngineApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes a new
        // ApplicationContext and registers a CommandLinePropertySource to expose
        // command line arguments as Spring properties.
        SpringApplication.run(BusinessRuleEngineApplication.class, args);
    }
}