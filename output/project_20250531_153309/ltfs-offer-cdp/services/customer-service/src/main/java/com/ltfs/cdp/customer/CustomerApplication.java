package com.ltfs.cdp.customer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Customer Service.
 * This service is part of the LTFS Offer CDP (Customer Data Platform) project,
 * responsible for managing customer profiles, deduplication, and providing a single customer view.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.customer} package, allowing it to find and register controllers, services,
 *         repositories, and other components.</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.customer"}) // Explicitly define base package for component scanning
public class CustomerApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses {@link SpringApplication#run(Class, String...)} to bootstrap and launch
     * the Customer Service application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, and then calls the run method of any ApplicationRunner or CommandLineRunner beans.
        SpringApplication.run(CustomerApplication.class, args);
    }
}