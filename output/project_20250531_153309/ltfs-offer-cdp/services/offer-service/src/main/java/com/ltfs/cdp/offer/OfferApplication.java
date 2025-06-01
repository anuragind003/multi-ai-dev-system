package com.ltfs.cdp.offer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Offer Service.
 * This service is part of the LTFS Offer CDP (Customer Data Platform) project.
 * It is responsible for managing offer-related functionalities, including
 * processing, validation, and deduplication of offers for various consumer loan products.
 *
 * The `@SpringBootApplication` annotation is a convenience annotation that adds:
 * - `@Configuration`: Tags the class as a source of bean definitions for the application context.
 * - `@EnableAutoConfiguration`: Tells Spring Boot to start adding beans based on classpath settings,
 *   other beans, and various property settings. For example, if `spring-webmvc` is on the classpath,
 *   this annotation flags the application as a web application and sets up a DispatcherServlet.
 * - `@ComponentScan`: Tells Spring to look for other components, configurations, and services
 *   in the `com.ltfs.cdp.offer` package, allowing it to find and register controllers, services,
 *   repositories, etc.
 *
 * The `@ComponentScan` is explicitly added here to ensure that all necessary components
 * within the `com.ltfs.cdp.offer` package and its sub-packages are discovered and registered
 * as Spring beans.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.offer")
public class OfferApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses `SpringApplication.run()` to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Starts the Spring application.
        // The first argument is the primary Spring application class (this class).
        // The second argument is the command-line arguments to be passed to the application.
        SpringApplication.run(OfferApplication.class, args);
    }
}