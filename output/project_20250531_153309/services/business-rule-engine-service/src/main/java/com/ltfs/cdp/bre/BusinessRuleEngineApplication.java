package com.ltfs.cdp.bre;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * Main Spring Boot application class for the Business Rule Engine Service.
 * This service is a core component of the LTFS Offer CDP (Customer Data Platform)
 * responsible for applying various business rules, including:
 * <ul>
 *     <li>Basic column-level validation on data moving from Offermart to CDP System.</li>
 *     <li>Deduplication logic across all Consumer Loan (CL) products (Loyalty, Preapproved, E-aggregator etc.).</li>
 *     <li>Deduplication against the 'live book' (Customer 360) before offers are finalized.</li>
 *     <li>Specific deduplication rules for top-up loan offers.</li>
 * </ul>
 *
 * <p>Annotated with {@code @SpringBootApplication} which is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the {@code com.ltfs.cdp.bre} package, allowing it to find and register controllers, services,
 *         repositories, etc.</li>
 * </ul>
 * </p>
 * <p>Annotated with {@code @EnableDiscoveryClient} to enable service registration and discovery.
 * This allows the Business Rule Engine Service to register itself with a discovery server (e.g., Eureka)
 * and for other microservices to locate and communicate with it, adhering to the microservices architecture.</p>
 */
@SpringBootApplication
@EnableDiscoveryClient // Enables service registration and discovery for microservices architecture
public class BusinessRuleEngineApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It bootstraps and launches the Business Rule Engine Service.
     *
     * @param args Command line arguments passed to the application. These are typically
     *             used for external configuration or profile activation.
     */
    public static void main(String[] args) {
        // Runs the Spring Boot application. This static method creates and runs a
        // suitable ApplicationContext instance.
        SpringApplication.run(BusinessRuleEngineApplication.class, args);
    }
}