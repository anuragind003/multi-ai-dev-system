package com.ltfs.cdp.offer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Offer Service.
 * This service is part of the LTFS Offer CDP (Customer Data Platform) project,
 * responsible for managing and processing offer-related data.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.offer} package, allowing it to find and register controllers, services,
 *         repositories, etc.</li>
 * </ul>
 *
 * <p>The {@code @ComponentScan} is explicitly added here to ensure that all necessary components
 * within the defined base package and its sub-packages are discovered and registered by Spring.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.offer")
public class OfferApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot Offer Service application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, and then calls the run method of all registered ApplicationRunners.
        SpringApplication.run(OfferApplication.class, args);
    }
}