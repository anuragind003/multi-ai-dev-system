package com.ltfs.cdp.gateway.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.config.annotation.method.configuration.EnableReactiveMethodSecurity;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.ReactiveJwtAuthenticationConverterAdapter;
import org.springframework.security.web.server.SecurityWebFilterChain;
import reactor.core.publisher.Mono;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Security configuration for the API Gateway service.
 * This class configures OAuth2/OpenID Connect integration, handling authentication
 * and authorization at the gateway level using Spring Security's reactive capabilities.
 * It acts as a Resource Server, validating JWT tokens for incoming requests.
 *
 * The gateway is responsible for securing access to downstream microservices by
 * ensuring that only authenticated and authorized requests with valid JWT tokens
 * are allowed to proceed.
 */
@Configuration
@EnableWebFluxSecurity // Enables Spring Security for Spring WebFlux applications
@EnableReactiveMethodSecurity // Enables method-level security annotations like @PreAuthorize
public class SecurityConfig {

    /**
     * Configures the security filter chain for the API Gateway.
     * This bean defines the security rules and authentication mechanisms for incoming requests.
     *
     * @param http The ServerHttpSecurity object to configure security for reactive web applications.
     * @return A SecurityWebFilterChain that defines the security rules.
     */
    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        http
            // Disable CSRF (Cross-Site Request Forgery) protection.
            // This is common for stateless REST APIs where JWTs are used for authentication,
            // as CSRF tokens are typically managed by the client and not needed.
            .csrf(ServerHttpSecurity.CsrfSpec::disable)

            // Configure authorization rules for different request paths.
            .authorizeExchange(exchanges -> exchanges
                // Permit all requests to actuator endpoints (e.g., /actuator/health, /actuator/info).
                // These are often used for monitoring and should be publicly accessible.
                .pathMatchers("/actuator/**").permitAll()
                // Permit all requests to Swagger UI and OpenAPI documentation endpoints.
                // This allows developers to access API documentation without authentication.
                .pathMatchers("/swagger-ui.html", "/swagger-ui/**", "/v3/api-docs/**", "/webjars/**").permitAll()
                // All other requests must be authenticated.
                // This ensures that any request not explicitly permitted requires a valid JWT.
                .anyExchange().authenticated()
            )
            // Configure OAuth2 Resource Server to validate JWT tokens.
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    // Set a custom JWT authentication converter.
                    // This converter is crucial for extracting authorities (roles) from the JWT claims.
                    .jwtAuthenticationConverter(jwtAuthenticationConverter())
                )
            );
        return http.build();
    }

    /**
     * Defines a custom JWT authentication converter.
     * This converter is responsible for extracting roles/authorities from the JWT claims
     * and mapping them to Spring Security's GrantedAuthority objects.
     *
     * It typically looks for roles in 'realm_access.roles' (for realm roles) and
     * 'resource_access.<client-id>.roles' (for client-specific roles), which are common
     * in Keycloak setups.
     *
     * @return A Converter that transforms a Jwt into a Mono of AbstractAuthenticationToken.
     */
    @Bean
    public Converter<Jwt, Mono<AbstractAuthenticationToken>> jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            // Initialize an empty stream for collecting all authorities.
            Stream<String> authoritiesStream = Stream.empty();

            // 1. Extract realm roles (e.g., from Keycloak's 'realm_access' claim).
            // This claim typically contains roles assigned directly to the user within the realm.
            Optional.ofNullable(jwt.getClaimAsMap("realm_access"))
                .map(realmAccess -> (Collection<String>) realmAccess.get("roles"))
                .orElse(Collections.emptyList())
                .forEach(role -> authoritiesStream = Stream.concat(authoritiesStream, Stream.of(role)));

            // 2. Extract client-specific roles (e.g., from Keycloak's 'resource_access' claim).
            // This claim contains roles assigned to the user for specific client applications.
            // Replace 'api-gateway-service' with the actual client ID configured in your
            // OAuth2/OpenID Connect provider (e.g., Keycloak) for this API Gateway service.
            final String API_GATEWAY_CLIENT_ID = "api-gateway-service"; // IMPORTANT: Configure your actual client ID here
            Optional.ofNullable(jwt.getClaimAsMap("resource_access"))
                .map(resourceAccess -> (Map<String, Object>) resourceAccess.get(API_GATEWAY_CLIENT_ID))
                .map(clientAccess -> (Collection<String>) clientAccess.get("roles"))
                .orElse(Collections.emptyList())
                .forEach(role -> authoritiesStream = Stream.concat(authoritiesStream, Stream.of(role)));

            // Map the collected role strings to Spring Security's SimpleGrantedAuthority objects.
            // Roles are typically prefixed with "ROLE_" in Spring Security for role-based authorization.
            // Convert roles to uppercase for consistency.
            return authoritiesStream
                .distinct() // Ensure unique roles
                .map(role -> new SimpleGrantedAuthority("ROLE_" + role.toUpperCase()))
                .collect(Collectors.toList());
        });
        // Wrap the synchronous JwtAuthenticationConverter in a ReactiveJwtAuthenticationConverterAdapter
        // to make it compatible with Spring Security's reactive chain.
        return new ReactiveJwtAuthenticationConverterAdapter(converter);
    }
}