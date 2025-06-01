package com.ltfs.cdp.datavalidation;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Data Validation Service.
 * This service is responsible for performing basic column-level validation
 * on data moving from the Offermart system to the CDP (Customer Data Platform) System.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.datavalidation} package, allowing it to find and register controllers,
 *         services, and repositories.</li>
 * </ul>
 *
 * <p>The {@code @ComponentScan} is explicitly added here to ensure that Spring scans
 * components within this package and its sub-packages.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.datavalidation")
public class DataValidationApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses {@link SpringApplication#run(Class, String...)} to bootstrap and launch
     * the Data Validation Service.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, loading all beans and starting the embedded web server (if applicable).
        SpringApplication.run(DataValidationApplication.class, args);
    }
}