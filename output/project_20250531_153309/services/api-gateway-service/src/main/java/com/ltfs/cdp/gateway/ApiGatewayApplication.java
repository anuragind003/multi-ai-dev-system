package com.ltfs.cdp.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main Spring Boot application class for the API Gateway service.
 * This class serves as the entry point for the API Gateway microservice,
 * enabling routing, security, and other cross-cutting concerns for
 * requests to downstream services in the LTFS Offer CDP system.
 *
 * The `@SpringBootApplication` annotation is a convenience annotation that adds:
 * - `@Configuration`: Tags the class as a source of bean definitions for the application context.
 * - `@EnableAutoConfiguration`: Tells Spring Boot to start adding beans based on classpath settings,
 *   other beans, and various property settings. For an API Gateway, this would typically
 *   auto-configure embedded servers, Spring Cloud Gateway components (if used), etc.
 * - `@ComponentScan`: Tells Spring to look for other components, configurations, and services
 *   in the `com.ltfs.cdp.gateway` package, allowing it to discover and register beans.
 */
@SpringBootApplication
public class ApiGatewayApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the API Gateway application.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, loading all beans and starting the embedded server (e.g., Netty, Tomcat).
        SpringApplication.run(ApiGatewayApplication.class, args);
    }

}