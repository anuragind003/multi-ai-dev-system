package com.ltfs.cdp.offer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Offer Service.
 * This class serves as the entry point for the microservice,
 * responsible for managing customer offers within the LTFS CDP system.
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
 * </p>
 *
 * <p>This service is a key component of the LTFS Offer CDP, aiming to streamline
 * offer management, deduplication, and customer profile integration for consumer loan products.</p>
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.offer"}) // Explicitly define base package for component scanning
public class OfferApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses {@link SpringApplication#run(Class, String...)} to bootstrap and launch
     * the Offer Service application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes the Spring application context,
        // performs classpath scanning, and starts the embedded web server (if applicable).
        SpringApplication.run(OfferApplication.class, args);
    }
}