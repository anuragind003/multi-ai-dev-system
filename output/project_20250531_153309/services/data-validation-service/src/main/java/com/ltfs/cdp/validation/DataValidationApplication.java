package com.ltfs.cdp.validation;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main Spring Boot application class for the Data Validation Service.
 * This service is responsible for performing basic column-level validation
 * on data moving from Offermart to the CDP System, as well as handling
 * deduplication logic for customer and offer data.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.validation} package, allowing it to find controllers, services, and other components.</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
public class DataValidationApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses {@link SpringApplication#run(Class, String...)} to bootstrap and launch
     * the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        SpringApplication.run(DataValidationApplication.class, args);
    }
}