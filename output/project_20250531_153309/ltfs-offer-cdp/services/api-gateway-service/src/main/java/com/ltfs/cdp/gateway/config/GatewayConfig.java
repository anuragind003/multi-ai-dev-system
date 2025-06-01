package com.ltfs.cdp.gateway.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration class for Spring Cloud Gateway.
 * This class defines the routing rules, predicates, and filters for incoming requests,
 * directing them to the appropriate downstream microservices within the LTFS Offer CDP ecosystem.
 *
 * It leverages Spring Cloud Gateway's fluent API to configure routes dynamically.
 */
@Configuration
public class GatewayConfig {

    /**
     * Configures the custom routes for the API Gateway.
     * This method defines how requests are matched (predicates) and how they are processed
     * (filters) before being forwarded to the target microservice.
     *
     * @param builder The {@link RouteLocatorBuilder} used to construct the routes.
     * @return A {@link RouteLocator} instance containing all defined routes.
     */
    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                // Route for Customer Service
                // Handles requests to /api/v1/customers/**
                // Example: A request to /api/v1/customers/123 will be routed to customer-service/customers/123
                .route("customer_service_route", r -> r.path("/api/v1/customers/**")
                        // Apply filters:
                        // 1. RewritePath: Removes the /api/v1 prefix from the path before forwarding.
                        //    The regex `/(?<segment>.*)` captures everything after /api/v1/ into a named group 'segment'.
                        //    The replacement `/${segment}` then uses this captured part as the new path.
                        .filters(f -> f.rewritePath("/api/v1/(?<segment>.*)", "/${segment}"))
                        // Target URI: 'lb://customer-service' indicates a load-balanced URI
                        // where 'customer-service' is the logical service ID registered with a discovery server (e.g., Eureka).
                        .uri("lb://customer-service"))

                // Route for Offer Service
                // Handles requests to /api/v1/offers/**
                // Example: A request to /api/v1/offers/create will be routed to offer-service/offers/create
                .route("offer_service_route", r -> r.path("/api/v1/offers/**")
                        // Apply filters:
                        // 1. RewritePath: Removes the /api/v1 prefix from the path before forwarding.
                        .filters(f -> f.rewritePath("/api/v1/(?<segment>.*)", "/${segment}"))
                        // Target URI: 'lb://offer-service' for load balancing to the offer microservice.
                        .uri("lb://offer-service"))

                // Route for Campaign Service
                // Handles requests to /api/v1/campaigns/**
                // Example: A request to /api/v1/campaigns/active will be routed to campaign-service/campaigns/active
                .route("campaign_service_route", r -> r.path("/api/v1/campaigns/**")
                        // Apply filters:
                        // 1. RewritePath: Removes the /api/v1 prefix from the path before forwarding.
                        .filters(f -> f.rewritePath("/api/v1/(?<segment>.*)", "/${segment}"))
                        // Target URI: 'lb://campaign-service' for load balancing to the campaign microservice.
                        .uri("lb://campaign-service"))

                // Add more routes here as the project expands and new microservices are introduced.
                // For example, a route for a validation service or a deduplication service.
                // .route("validation_service_route", r -> r.path("/api/v1/validate/**")
                //         .filters(f -> f.rewritePath("/api/v1/(?<segment>.*)", "/${segment}"))
                //         .uri("lb://validation-service"))

                .build(); // Builds the RouteLocator with all defined routes.
    }
}