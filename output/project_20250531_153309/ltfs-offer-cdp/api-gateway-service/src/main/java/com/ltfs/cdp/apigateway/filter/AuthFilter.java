package com.ltfs.cdp.apigateway.filter;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.security.Key;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.function.Function;

/**
 * Custom filter for JWT validation and propagating user context to downstream services.
 * This filter intercepts incoming requests, validates the JWT token present in the
 * Authorization header, and if valid, adds user-specific information (like username and roles)
 * to the request headers before forwarding it to the target service.
 * Requests to public/excluded paths are bypassed from authentication.
 *
 * <p>To configure this filter, ensure the following properties are set in your
 * application.properties or application.yml:
 * <ul>
 *     <li>{@code jwt.secret}: A base64 encoded secret key for JWT signing.</li>
 *     <li>{@code auth.excluded-urls}: A comma-separated list of URL patterns (regex)
 *         that should bypass authentication (e.g., {@code /auth/login,/actuator/**}).</li>
 * </ul>
 * </p>
 */
@Component
public class AuthFilter implements GatewayFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(AuthFilter.class);

    // JWT secret key injected from application properties.
    // This key is used for signing and verifying JWT tokens.
    @Value("${jwt.secret}")
    private String jwtSecret;

    // List of public URLs that do not require authentication.
    // These paths will bypass the JWT validation logic.
    @Value("${auth.excluded-urls:/auth/login,/auth/register,/actuator/**}")
    private String[] excludedUrls;

    /**
     * Main filter logic.
     * This method is invoked for every incoming request to the API Gateway.
     *
     * @param exchange The current server web exchange, providing access to request and response.
     * @param chain The gateway filter chain, used to pass the request to the next filter or target service.
     * @return A Mono<Void> indicating completion of the filter processing.
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        // Check if the request path matches any of the configured excluded URLs.
        // If it's an excluded path, authentication is bypassed.
        if (isExcluded(path)) {
            log.debug("Bypassing authentication for excluded path: {}", path);
            return chain.filter(exchange); // Continue without authentication
        }

        // Extract Authorization header from the request.
        List<String> authHeaders = request.getHeaders().get(HttpHeaders.AUTHORIZATION);

        // Validate the presence and format of the Authorization header.
        // It must start with "Bearer ".
        if (authHeaders == null || authHeaders.isEmpty() || !authHeaders.get(0).startsWith("Bearer ")) {
            log.warn("Missing or invalid Authorization header for path: {}", path);
            // If header is missing or malformed, return UNAUTHORIZED response.
            return onError(exchange, "Missing or invalid Authorization header", HttpStatus.UNAUTHORIZED);
        }

        // Extract the JWT token by removing the "Bearer " prefix.
        String token = authHeaders.get(0).substring(7);

        try {
            // Validate the JWT token using the configured secret key.
            validateToken(token);

            // Extract claims (payload) from the validated JWT token.
            Claims claims = extractAllClaims(token);
            String username = claims.getSubject(); // Typically, 'sub' claim holds the username/user ID.
            // Assuming roles are stored as a list in a custom claim named "roles".
            List<String> roles = claims.get("roles", List.class);

            log.debug("JWT validated for user: {} with roles: {}", username, roles);

            // Build a new request with user context propagated as custom headers.
            // These headers can then be read by downstream microservices.
            ServerHttpRequest modifiedRequest = request.mutate()
                    .header("X-User-ID", username) // Propagate username as user ID
                    .header("X-User-Roles", String.join(",", roles)) // Propagate roles as a comma-separated string
                    .build();

            // Continue the filter chain with the modified request.
            return chain.filter(exchange.mutate().request(modifiedRequest).build());

        } catch (Exception e) {
            // Catch any exception during JWT validation (e.g., expired, invalid signature).
            log.error("JWT validation failed for path: {}. Error: {}", path, e.getMessage());
            // Return UNAUTHORIZED response with the error message.
            return onError(exchange, "Unauthorized: " + e.getMessage(), HttpStatus.UNAUTHORIZED);
        }
    }

    /**
     * Defines the order of this filter in the filter chain.
     * Filters with a lower order value have higher precedence and run earlier.
     * Setting it to HIGHEST_PRECEDENCE ensures it runs very early in the chain.
     *
     * @return The order value.
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }

    /**
     * Handles errors by setting the response status and completing the response.
     * This method is called when authentication fails.
     *
     * @param exchange The current server web exchange.
     * @param err The error message to log.
     * @param httpStatus The HTTP status to set in the response (e.g., UNAUTHORIZED, FORBIDDEN).
     * @return A Mono<Void> indicating completion of the response.
     */
    private Mono<Void> onError(ServerWebExchange exchange, String err, HttpStatus httpStatus) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(httpStatus);
        log.error("Responding with error: {} - {}", httpStatus, err);
        return response.setComplete(); // Complete the response, preventing further processing.
    }

    /**
     * Checks if the given request path is in the list of excluded URLs.
     * Uses regular expression matching for flexibility.
     *
     * @param path The request path to check.
     * @return True if the path matches any of the excluded URL patterns, false otherwise.
     */
    private boolean isExcluded(String path) {
        return Arrays.stream(excludedUrls).anyMatch(path::matches);
    }

    // --- JWT Utility Methods (simplified for direct inclusion within the filter) ---
    // In a larger project, these methods would typically reside in a dedicated JwtService or JwtUtil class.

    /**
     * Validates the JWT token.
     * This method parses the token and verifies its signature and expiration.
     *
     * @param token The JWT token string.
     * @throws io.jsonwebtoken.ExpiredJwtException if the token is expired.
     * @throws io.jsonwebtoken.SignatureException if the token signature is invalid.
     * @throws io.jsonwebtoken.MalformedJwtException if the token is not a valid JWT.
     * @throws IllegalArgumentException if the token is null or empty.
     */
    private void validateToken(String token) {
        // parseClaimsJws() method automatically validates signature and expiration.
        Jwts.parserBuilder().setSigningKey(getSignKey()).build().parseClaimsJws(token);
        // An explicit check for expiration can be added if specific handling is needed,
        // but the above line typically throws ExpiredJwtException.
        if (isTokenExpired(token)) {
            throw new RuntimeException("JWT Token has expired");
        }
    }

    /**
     * Extracts all claims (payload) from the JWT token.
     *
     * @param token The JWT token string.
     * @return The Claims object containing all token claims.
     */
    private Claims extractAllClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(getSignKey())
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    /**
     * Extracts a specific claim from the token using a resolver function.
     * This is a generic helper method for extracting individual claims.
     *
     * @param token The JWT token string.
     * @param claimsResolver The function to resolve the claim from the Claims object.
     * @param <T> The type of the claim.
     * @return The extracted claim.
     */
    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    /**
     * Extracts the expiration date from the token's claims.
     *
     * @param token The JWT token string.
     * @return The expiration Date.
     */
    private Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    /**
     * Checks if the token is expired by comparing its expiration date with the current date.
     *
     * @param token The JWT token string.
     * @return True if the token is expired, false otherwise.
     */
    private Boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }

    /**
     * Retrieves the signing key from the base64 encoded secret.
     * This key is used for signing and verifying JWT tokens.
     *
     * @return The signing Key.
     */
    private Key getSignKey() {
        byte[] keyBytes = Decoders.BASE64.decode(jwtSecret);
        return Keys.hmacShaKeyFor(keyBytes);
    }
}