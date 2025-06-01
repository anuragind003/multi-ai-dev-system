package com.ltfs.cdp.validation;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main Spring Boot application class for the Data Validation Service.
 * This service is responsible for performing basic column-level validation
 * on data moving from the Offermart system to the CDP (Customer Data Platform) system.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.validation} package, allowing it to find and register controllers, services, etc.</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
public class DataValidationApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch a Spring application
     * from a Java main method.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Starts the Spring Boot application.
        // The first argument is the primary Spring application class,
        // and the second argument passes any command-line arguments.
        SpringApplication.run(DataValidationApplication.class, args);
    }
}