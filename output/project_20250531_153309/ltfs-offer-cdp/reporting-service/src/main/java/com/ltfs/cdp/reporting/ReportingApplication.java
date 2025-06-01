package com.ltfs.cdp.reporting;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main Spring Boot application class for the Reporting Service.
 * This service is a core component of the LTFS Offer CDP (Customer Data Platform) project,
 * designed to provide comprehensive reporting and analytical views of customer, campaign,
 * and offer data. It integrates with other microservices within the CDP ecosystem
 * to deliver insights into customer profiles, offer performance, and campaign effectiveness.
 *
 * <p>The {@code @SpringBootApplication} annotation is a convenience annotation that combines:
 * <ul>
 *     <li>{@code @Configuration}: Designates this class as a source of bean definitions.</li>
 *     <li>{@code @EnableAutoConfiguration}: Automatically configures the Spring application
 *         based on the JAR dependencies that have been added. For example, if H2 is on the classpath,
 *         and you haven't configured any database connections, Spring Boot auto-configures an in-memory database.</li>
 *     <li>{@code @ComponentScan}: Scans for components, configurations, and services in the
 *         {@code com.ltfs.cdp.reporting} package and its sub-packages, allowing Spring to
 *         automatically discover and register beans.</li>
 * </ul>
 * </p>
 *
 * <p>As part of a microservices architecture, this application will typically expose RESTful APIs
 * for data retrieval and potentially consume events from other services (e.g., Customer Profile Service,
 * Offer Management Service) to build its reporting datasets.</p>
 */
@SpringBootApplication
public class ReportingApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * This method uses {@link org.springframework.boot.SpringApplication#run(Class, String...)}
     * to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application. These can be used
     *             to override properties defined in application.properties or application.yml.
     */
    public static void main(String[] args) {
        // Starts the Spring application context.
        // This will perform component scanning, auto-configuration, and bean creation,
        // making the application ready to serve requests.
        SpringApplication.run(ReportingApplication.class, args);
    }
}