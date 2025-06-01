package com.ltfs.cdp.customer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Customer Service.
 * This service is responsible for managing customer profiles,
 * performing deduplication, and providing a single view of the customer
 * for Consumer Loan Products within the LTFS Offer CDP system.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.customer} package, allowing it to find and register controllers, services,
 *         repositories, etc.</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.customer", "com.ltfs.cdp.common"}) // Assuming common utilities might be in a shared package
public class CustomerApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, and then calls the run method on any ApplicationRunner or
        // CommandLineRunner beans.
        SpringApplication.run(CustomerApplication.class, args);
    }
}