package com.ltfs.cdp.apigateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient; // For service registration/discovery if using Eureka/Consul
import org.springframework.cloud.netflix.zuul.EnableZuulProxy; // For enabling Zuul API Gateway features

/**
 * Main Spring Boot application class for the API Gateway Service.
 * This class serves as the entry point for the API Gateway,
 * enabling dynamic routing, monitoring, resiliency, security,
 * and more for the microservices within the LTFS Offer CDP ecosystem.
 *
 * <p>
 * {@code @SpringBootApplication} is a convenience annotation that adds:
 * <ul>
 *     <li>{@code @Configuration}: Tags the class as a source of bean definitions for the application context.</li>
 *     <li>{@code @EnableAutoConfiguration}: Tells Spring Boot to start adding beans based on classpath settings,
 *         other beans, and various property settings.</li>
 *     <li>{@code @ComponentScan}: Tells Spring to look for other components, configurations, and services
 *         in the `com.ltfs.cdp.apigateway` package, allowing it to find and register controllers, services, etc.</li>
 * </ul>
 * </p>
 *
 * <p>
 * {@code @EnableDiscoveryClient} enables service registration and discovery.
 * If using a discovery server like Eureka, this annotation allows the API Gateway
 * to register itself with the discovery server and discover other microservices.
 * </p>
 *
 * <p>
 * {@code @EnableZuulProxy} enables the Zuul proxy functionality. This annotation
 * turns the application into a Zuul proxy server, allowing it to route requests
 * to other microservices based on configured routes. It also integrates with
 * Netflix Hystrix for circuit breaking and Ribbon for client-side load balancing.
 * </p>
 */
@SpringBootApplication
@EnableDiscoveryClient // Enables this service to register with a discovery server (e.g., Eureka)
@EnableZuulProxy     // Enables Zuul as an API Gateway proxy
public class ApiGatewayApplication {

    /**
     * The main method that serves as the entry point for the Spring Boot application.
     * It uses SpringApplication.run() to bootstrap and launch the API Gateway service.
     *
     * @param args Command line arguments passed to the application.
     */
    public static void main(String[] args) {
        // Run the Spring Boot application. This method creates and refreshes an appropriate
        // ApplicationContext, loading all beans and configurations.
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}