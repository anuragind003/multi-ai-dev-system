package com.ltfs.cdp.adminportal;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the LTFS Offer CDP Admin Portal Service.
 * This class serves as the entry point for the Admin Portal microservice,
 * responsible for managing customer, campaign, and offer data within the CDP system.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings. For example, if {@code spring-webmvc} is on the classpath,
 *         this annotation flags the application as a web application and activates key behaviors such as setting up a {@code DispatcherServlet}.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services in the
 *         {@code com.ltfs.cdp.adminportal} package, allowing it to find controllers, services, repositories, etc.</li>
 * </ul>
 * </p>
 *
 * <p>This service is part of the LTFS Offer CDP project, aiming to streamline customer data management,
 * enable faster processing, and improve the overall management of customer, campaign, and offer data
 * for Consumer Loan Products.</p>
 */
@SpringBootApplication
@ComponentScan(basePackages = {"com.ltfs.cdp.adminportal"}) // Explicitly define base package for component scanning
public class AdminPortalApplication {

    /**
     * The main method which serves as the entry point for the Spring Boot application.
     * It uses {@link SpringApplication#run(Class, String...)} to bootstrap and launch
     * the Admin Portal Service.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application.
        // This method creates and refreshes an appropriate ApplicationContext,
        // and then runs all CommandLineRunner beans.
        SpringApplication.run(AdminPortalApplication.class, args);
    }
}