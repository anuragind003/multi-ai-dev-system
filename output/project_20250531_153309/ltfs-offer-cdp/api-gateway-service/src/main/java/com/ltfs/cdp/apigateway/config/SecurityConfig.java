package com.ltfs.cdp.apigateway.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * SecurityConfig class configures OAuth2/OpenID Connect security filters for the API Gateway.
 * It enables web security and defines security rules for incoming requests,
 * including JWT-based authentication and authorization.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Configures the security filter chain for HTTP requests.
     *
     * @param http The HttpSecurity object to configure.
     * @return A SecurityFilterChain instance.
     * @throws Exception if an error occurs during configuration.
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // Disable CSRF protection as it's generally not needed for stateless REST APIs
            // where tokens (JWT) are used for authentication.
            .csrf(csrf -> csrf.disable())
            // Configure session management to be stateless.
            // This ensures that no session is created or used by Spring Security,
            // which is typical for microservices using JWTs.
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // Authorize requests based on their paths.
            .authorizeHttpRequests(authorize -> authorize
                // Permit all requests to actuator endpoints (e.g., /actuator/health) for monitoring.
                .requestMatchers("/actuator/**").permitAll()
                // Permit all requests to Swagger UI and API documentation endpoints.
                // This allows clients to discover and interact with the API without authentication.
                .requestMatchers("/swagger-ui.html", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                // All other requests must be authenticated.
                .anyRequest().authenticated()
            )
            // Configure OAuth2 Resource Server to process JWT tokens.
            .oauth2ResourceServer(oauth2 -> oauth2
                // Use JWT for token validation.
                .jwt(jwt -> jwt
                    // Set a custom JWT authentication converter to extract authorities (roles) from the JWT.
                    // This allows for fine-grained authorization based on roles embedded in the token.
                    .jwtAuthenticationConverter(jwtAuthenticationConverter())
                )
            );
        return http.build();
    }

    /**
     * Defines a custom JwtAuthenticationConverter to extract authorities from JWT claims.
     * This converter is crucial for mapping JWT claims (e.g., 'realm_access.roles' from Keycloak)
     * to Spring Security's GrantedAuthority objects.
     *
     * @return A JwtAuthenticationConverter instance.
     */
    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        // Set a custom converter for granted authorities.
        converter.setJwtGrantedAuthoritiesConverter(this::extractAuthorities);
        return converter;
    }

    /**
     * Extracts authorities (roles) from a JWT token.
     * This method looks for roles in the 'realm_access.roles' claim (common in Keycloak)
     * and maps them to Spring Security's SimpleGrantedAuthority objects, prefixed with "ROLE_".
     *
     * @param jwt The JWT token.
     * @return A collection of GrantedAuthority objects.
     */
    private Collection<GrantedAuthority> extractAuthorities(Jwt jwt) {
        // Attempt to get the 'realm_access' claim as a map.
        Map<String, Object> realmAccess = jwt.getClaimAsMap("realm_access");
        if (realmAccess == null || !realmAccess.containsKey("roles")) {
            // If 'realm_access' or 'roles' claim is not found, return an empty list of authorities.
            return Collections.emptyList();
        }

        // Extract the 'roles' list from the 'realm_access' map.
        List<String> roles = (List<String>) realmAccess.get("roles");

        // Stream through the roles, prefix each with "ROLE_", convert to uppercase,
        // and map them to SimpleGrantedAuthority objects.
        return roles.stream()
                .map(role -> new SimpleGrantedAuthority("ROLE_" + role.toUpperCase()))
                .collect(Collectors.toList());
    }

    /**
     * Exposes the AuthenticationManager as a bean.
     * This can be useful if custom authentication logic needs to be invoked programmatically,
     * though less common when relying purely on OAuth2 Resource Server for token validation.
     *
     * @param authenticationConfiguration The AuthenticationConfiguration.
     * @return The AuthenticationManager instance.
     * @throws Exception if an error occurs.
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }
}