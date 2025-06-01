package com.ltfs.cdp.bre;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Business Rule Engine Service.
 * This service is responsible for applying business rules, such as deduplication
 * and validation, on customer and offer data within the LTFS Offer CDP system.
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
 * </p>
 *
 * <p>The {@code @ComponentScan} is explicitly used here to ensure that Spring scans
 * components within the defined package structure, which is a good practice for
 * microservices to clearly define their component scope.</p>
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.bre")
public class BusinessRuleEngineApplication {

    /**
     * The main method that serves as the entry point for the Business Rule Engine Service.
     * It uses Spring Boot's {@link SpringApplication#run(Class, String...)} method
     * to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, loading all beans and starting embedded servers (if any).
        SpringApplication.run(BusinessRuleEngineApplication.class, args);
    }
}