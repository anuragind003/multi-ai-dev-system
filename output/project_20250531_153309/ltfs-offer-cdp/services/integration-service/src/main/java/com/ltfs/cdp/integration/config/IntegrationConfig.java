package com.ltfs.cdp.integration.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Component;
import org.springframework.validation.annotation.Validated;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;

/**
 * Configuration class for external system integrations within the LTFS Offer CDP Integration Service.
 * This class loads properties related to various external APIs such as Offermart and Customer 360,
 * including their base URLs, API keys, and timeout settings.
 *
 * Properties are typically defined in `application.properties` or `application.yml` under
 * prefixes like `integration.offermart` and `integration.customer360`.
 *
 * To use these configurations in other services, simply autowire the respective nested
 * configuration class (e.g., `OffermartConfig` or `Customer360Config`).
 *
 * Example `application.yml` entries:
 * ```yaml
 * integration:
 *   offermart:
 *     baseUrl: http://offermart-service:8080/api/v1
 *     apiKey: your-offermart-api-key
 *     authHeaderName: X-API-Key
 *     authHeaderPrefix: ""
 *     connectionTimeoutMillis: 5000
 *     readTimeoutMillis: 10000
 *   customer360:
 *     baseUrl: http://customer360-service:8080/api/v1
 *     apiKey: your-customer360-api-key
 *     authHeaderName: Authorization
 *     authHeaderPrefix: Bearer
 *     connectionTimeoutMillis: 5000
 *     readTimeoutMillis: 10000
 * ```
 */
@Configuration
public class IntegrationConfig {

    /**
     * Configuration properties for the Offermart external service.
     * This service is responsible for providing initial customer and offer data
     * to be ingested into the CDP system.
     */
    @Component
    @ConfigurationProperties(prefix = "integration.offermart")
    @Validated // Enables JSR 303 validation for these properties
    public static class OffermartConfig {

        /**
         * The base URL for the Offermart API.
         * This is the root endpoint for all Offermart related API calls.
         * Example: `http://offermart-service:8080/api/v1`
         */
        @NotBlank(message = "Offermart base URL cannot be blank")
        private String baseUrl;

        /**
         * The API key required for authenticating with the Offermart service.
         * It is crucial to manage this securely, ideally via environment variables
         * or a secret management system in production environments.
         */
        @NotBlank(message = "Offermart API key cannot be blank")
        private String apiKey;

        /**
         * The name of the HTTP header used for sending the API key.
         * Common examples include "X-API-Key" or "Authorization".
         */
        @NotBlank(message = "Offermart authentication header name cannot be blank")
        private String authHeaderName;

        /**
         * An optional prefix for the authentication header value.
         * For example, if the API key needs to be sent as "Bearer YOUR_API_KEY",
         * this prefix would be "Bearer ". Defaults to an empty string if not specified.
         */
        private String authHeaderPrefix = ""; // Default to empty string if no prefix

        /**
         * The connection timeout in milliseconds for requests to the Offermart service.
         * This is the maximum time allowed to establish a connection to the remote host.
         * Must be at least 1000ms. Default is 5000ms (5 seconds).
         */
        @Min(value = 1000, message = "Offermart connection timeout must be at least 1000ms")
        private int connectionTimeoutMillis = 5000; // Default to 5 seconds

        /**
         * The read timeout in milliseconds for requests to the Offermart service.
         * This is the maximum time allowed to read data from an established connection.
         * Must be at least 1000ms. Default is 10000ms (10 seconds).
         */
        @Min(value = 1000, message = "Offermart read timeout must be at least 1000ms")
        private int readTimeoutMillis = 10000; // Default to 10 seconds

        // --- Getters for OffermartConfig properties ---
        public String getBaseUrl() {
            return baseUrl;
        }

        public String getApiKey() {
            return apiKey;
        }

        public String getAuthHeaderName() {
            return authHeaderName;
        }

        public String getAuthHeaderPrefix() {
            return authHeaderPrefix;
        }

        public int getConnectionTimeoutMillis() {
            return connectionTimeoutMillis;
        }

        public int getReadTimeoutMillis() {
            return readTimeoutMillis;
        }

        // --- Setters for OffermartConfig properties (required by @ConfigurationProperties) ---
        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public void setApiKey(String apiKey) {
            this.apiKey = apiKey;
        }

        public void setAuthHeaderName(String authHeaderName) {
            this.authHeaderName = authHeaderName;
        }

        public void setAuthHeaderPrefix(String authHeaderPrefix) {
            this.authHeaderPrefix = authHeaderPrefix;
        }

        public void setConnectionTimeoutMillis(int connectionTimeoutMillis) {
            this.connectionTimeoutMillis = connectionTimeoutMillis;
        }

        public void setReadTimeoutMillis(int readTimeoutMillis) {
            this.readTimeoutMillis = readTimeoutMillis;
        }
    }

    /**
     * Configuration properties for the Customer 360 external service.
     * This service is crucial for performing deduplication against the 'live book'
     * of customer data, ensuring a single profile view.
     */
    @Component
    @ConfigurationProperties(prefix = "integration.customer360")
    @Validated // Enables JSR 303 validation for these properties
    public static class Customer360Config {

        /**
         * The base URL for the Customer 360 API.
         * This is the root endpoint for all Customer 360 related API calls.
         * Example: `http://customer360-service:8080/api/v1`
         */
        @NotBlank(message = "Customer 360 base URL cannot be blank")
        private String baseUrl;

        /**
         * The API key required for authenticating with the Customer 360 service.
         * It is crucial to manage this securely, ideally via environment variables
         * or a secret management system in production environments.
         */
        @NotBlank(message = "Customer 360 API key cannot be blank")
        private String apiKey;

        /**
         * The name of the HTTP header used for sending the API key.
         * Common examples include "X-API-Key" or "Authorization".
         */
        @NotBlank(message = "Customer 360 authentication header name cannot be blank")
        private String authHeaderName;

        /**
         * An optional prefix for the authentication header value.
         * For example, if the API key needs to be sent as "Bearer YOUR_API_KEY",
         * this prefix would be "Bearer ". Defaults to an empty string if not specified.
         */
        private String authHeaderPrefix = ""; // Default to empty string if no prefix

        /**
         * The connection timeout in milliseconds for requests to the Customer 360 service.
         * This is the maximum time allowed to establish a connection to the remote host.
         * Must be at least 1000ms. Default is 5000ms (5 seconds).
         */
        @Min(value = 1000, message = "Customer 360 connection timeout must be at least 1000ms")
        private int connectionTimeoutMillis = 5000; // Default to 5 seconds

        /**
         * The read timeout in milliseconds for requests to the Customer 360 service.
         * This is the maximum time allowed to read data from an established connection.
         * Must be at least 1000ms. Default is 10000ms (10 seconds).
         */
        @Min(value = 1000, message = "Customer 360 read timeout must be at least 1000ms")
        private int readTimeoutMillis = 10000; // Default to 10 seconds

        // --- Getters for Customer360Config properties ---
        public String getBaseUrl() {
            return baseUrl;
        }

        public String getApiKey() {
            return apiKey;
        }

        public String getAuthHeaderName() {
            return authHeaderName;
        }

        public String getAuthHeaderPrefix() {
            return authHeaderPrefix;
        }

        public int getConnectionTimeoutMillis() {
            return connectionTimeoutMillis;
        }

        public int getReadTimeoutMillis() {
            return readTimeoutMillis;
        }

        // --- Setters for Customer360Config properties (required by @ConfigurationProperties) ---
        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public void setApiKey(String apiKey) {
            this.apiKey = apiKey;
        }

        public void setAuthHeaderName(String authHeaderName) {
            this.authHeaderName = authHeaderName;
        }

        public void setAuthHeaderPrefix(String authHeaderPrefix) {
            this.authHeaderPrefix = authHeaderPrefix;
        }

        public void setConnectionTimeoutMillis(int connectionTimeoutMillis) {
            this.connectionTimeoutMillis = connectionTimeoutMillis;
        }

        public void setReadTimeoutMillis(int readTimeoutMillis) {
            this.readTimeoutMillis = readTimeoutMillis;
        }
    }
}