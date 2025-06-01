package com.ltfs.cdp.campaign;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Main Spring Boot application class for the Campaign Service.
 * This class serves as the entry point for the microservice.
 *
 * The `@SpringBootApplication` annotation is a convenience annotation that adds:
 * - `@Configuration`: Tags the class as a source of bean definitions for the application context.
 * - `@EnableAutoConfiguration`: Tells Spring Boot to start adding beans based on classpath settings,
 *   other beans, and various property settings. For example, if `spring-webmvc` is on the classpath,
 *   this annotation flags the application as a web application and activates key behaviors
 *   such as setting up a `DispatcherServlet`.
 * - `@ComponentScan`: Tells Spring to look for other components, configurations, and services
 *   in the `com.ltfs.cdp.campaign` package, allowing it to find and register controllers,
 *   services, repositories, etc.
 *
 * As part of the LTFS Offer CDP project, this service manages campaign-related data
 * and operations, contributing to the overall goal of faster processing and improved
 * management of customer, campaign, and offer data.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.ltfs.cdp.campaign") // Explicitly define base package for component scanning
public class CampaignApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses `SpringApplication.run()` to bootstrap and launch the application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Runs the Spring Boot application.
        // The first argument is the primary Spring application class, and the second
        // argument is the command-line arguments to be passed to the application.
        SpringApplication.run(CampaignApplication.class, args);
    }

}