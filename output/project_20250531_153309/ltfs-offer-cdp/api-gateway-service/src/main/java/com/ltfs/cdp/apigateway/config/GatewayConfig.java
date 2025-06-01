package com.ltfs.cdp.apigateway.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;

/**
 * Configuration class for defining API Gateway routing rules and global filters.
 * This class uses Spring Cloud Gateway to manage incoming requests,
 * routing them to appropriate downstream microservices based on defined predicates
 * and applying various filters for cross-cutting concerns like security,
 * resilience (circuit breaker), and path manipulation.
 */
@Configuration
public class GatewayConfig {

    /**
     * Defines the routing rules for the API Gateway.
     * Each route specifies a predicate (e.g., path, method) to match incoming requests
     * and a URI to forward the request to, along with optional filters.
     *
     * @param builder The RouteLocatorBuilder used to construct the routes.
     * @return A RouteLocator instance containing all defined routes.
     */
    @Bean
    public RouteLocator routeLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                // Route for Customer Service
                // Matches requests starting with /api/v1/customers/
                // Strips the /api/v1 prefix before forwarding to the customer-service
                // Applies a Circuit Breaker for resilience and a Retry mechanism
                .route("customer_service_route", r -> r.path("/api/v1/customers/**")
                        .filters(f -> f.stripPrefix(2) // Strips "/api/v1"
                                .circuitBreaker(config -> config
                                        .setName("customerServiceCircuitBreaker")
                                        .setFallbackUri("forward:/fallback/customer")) // Fallback URI for customer service
                                .retry(retryConfig -> retryConfig.setRetries(3)
                                        .setStatuses(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                                                org.springframework.http.HttpStatus.BAD_GATEWAY,
                                                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE)))
                        .uri("lb://CUSTOMER-SERVICE")) // Load balances requests to CUSTOMER-SERVICE

                // Route for Offer Service
                // Matches requests starting with /api/v1/offers/
                // Strips the /api/v1 prefix and applies resilience filters
                .route("offer_service_route", r -> r.path("/api/v1/offers/**")
                        .filters(f -> f.stripPrefix(2) // Strips "/api/v1"
                                .circuitBreaker(config -> config
                                        .setName("offerServiceCircuitBreaker")
                                        .setFallbackUri("forward:/fallback/offer")) // Fallback URI for offer service
                                .retry(retryConfig -> retryConfig.setRetries(3)
                                        .setStatuses(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                                                org.springframework.http.HttpStatus.BAD_GATEWAY,
                                                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE)))
                        .uri("lb://OFFER-SERVICE")) // Load balances requests to OFFER-SERVICE

                // Route for Campaign Service
                // Matches requests starting with /api/v1/campaigns/
                // Strips the /api/v1 prefix and applies resilience filters
                .route("campaign_service_route", r -> r.path("/api/v1/campaigns/**")
                        .filters(f -> f.stripPrefix(2) // Strips "/api/v1"
                                .circuitBreaker(config -> config
                                        .setName("campaignServiceCircuitBreaker")
                                        .setFallbackUri("forward:/fallback/campaign")) // Fallback URI for campaign service
                                .retry(retryConfig -> retryConfig.setRetries(3)
                                        .setStatuses(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                                                org.springframework.http.HttpStatus.BAD_GATEWAY,
                                                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE)))
                        .uri("lb://CAMPAIGN-SERVICE")) // Load balances requests to CAMPAIGN-SERVICE

                // Route for Deduplication Service
                // Matches requests starting with /api/v1/dedupe/
                // Strips the /api/v1 prefix and applies resilience filters
                .route("dedupe_service_route", r -> r.path("/api/v1/dedupe/**")
                        .filters(f -> f.stripPrefix(2) // Strips "/api/v1"
                                .circuitBreaker(config -> config
                                        .setName("dedupeServiceCircuitBreaker")
                                        .setFallbackUri("forward:/fallback/dedupe")) // Fallback URI for dedupe service
                                .retry(retryConfig -> retryConfig.setRetries(3)
                                        .setStatuses(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                                                org.springframework.http.HttpStatus.BAD_GATEWAY,
                                                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE)))
                        .uri("lb://DEDUPE-SERVICE")) // Load balances requests to DEDUPE-SERVICE

                // Fallback route for general errors or unhandled paths
                // This route can be used to redirect to a generic error page or service
                .route("fallback_route", r -> r.path("/fallback/**")
                        .filters(f -> f.rewritePath("/fallback/(?<segment>.*)", "/error/${segment}"))
                        .uri("forward:/error")) // Forwards to a local error controller
                .build();
    }
}