package com.ltfs.cdp.integration.eaggregator;

import com.ltfs.cdp.integration.eaggregator.exception.EAggregatorApiException;
import com.ltfs.cdp.integration.eaggregator.exception.EAggregatorConnectionException;
import com.ltfs.cdp.integration.eaggregator.model.EAggregatorOfferRequest;
import com.ltfs.cdp.integration.eaggregator.model.EAggregatorOfferResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.Objects;

/**
 * Adapter for real-time API communication with E-aggregators.
 * This class handles sending requests to and receiving responses from external E-aggregator systems.
 * It uses Spring WebClient for non-blocking HTTP communication.
 */
@Service
public class EAggregatorApiAdapter {

    private static final Logger log = LoggerFactory.getLogger(EAggregatorApiAdapter.class);

    @Value("${eaggregator.api.base-url}")
    private String eAggregatorApiBaseUrl;

    @Value("${eaggregator.api.offer-endpoint:/offers}")
    private String offerEndpoint;

    @Value("${eaggregator.api.timeout-seconds:30}")
    private int apiTimeoutSeconds;

    @Value("${eaggregator.api.api-key:default-api-key}") // Example for an API key
    private String eAggregatorApiKey;

    private WebClient webClient;

    /**
     * Initializes the WebClient after properties are set.
     * This ensures the WebClient is configured with the correct base URL and timeouts.
     */
    @PostConstruct
    public void init() {
        this.webClient = WebClient.builder()
                .baseUrl(eAggregatorApiBaseUrl)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                // Add any required authentication headers, e.g., API Key
                .defaultHeader("X-API-Key", eAggregatorApiKey)
                .build();

        log.info("EAggregatorApiAdapter initialized with base URL: {} and timeout: {} seconds",
                eAggregatorApiBaseUrl, apiTimeoutSeconds);
    }

    /**
     * Sends an offer request to the E-aggregator API and retrieves the offer details.
     * This method handles the HTTP communication, including request serialization,
     * response deserialization, and error handling for various scenarios.
     *
     * @param request The EAggregatorOfferRequest containing the criteria for the offer.
     * @return A Mono emitting EAggregatorOfferResponse if the call is successful.
     * @throws EAggregatorConnectionException if there's a network or connection issue.
     * @throws EAggregatorApiException if the E-aggregator API returns an error status or invalid response.
     */
    public Mono<EAggregatorOfferResponse> getOfferDetails(EAggregatorOfferRequest request) {
        log.info("Sending offer request to E-aggregator for customer: {}", request.getCustomerId());

        return webClient.post()
                .uri(offerEndpoint)
                .bodyValue(request)
                .retrieve()
                .onStatus(HttpStatus::isError, response ->
                        response.bodyToMono(String.class)
                                .flatMap(errorBody -> {
                                    log.error("EAggregator API returned error status {}: {}", response.statusCode(), errorBody);
                                    return Mono.error(new EAggregatorApiException(
                                            String.format("EAggregator API error: %s - %s", response.statusCode(), errorBody),
                                            response.statusCode().value(),
                                            errorBody
                                    ));
                                })
                )
                .bodyToMono(EAggregatorOfferResponse.class)
                .timeout(Duration.ofSeconds(apiTimeoutSeconds)) // Apply timeout to the entire operation
                .doOnSuccess(response -> log.info("Successfully received offer response from E-aggregator for customer: {}", request.getCustomerId()))
                .doOnError(WebClientRequestException.class, ex -> {
                    log.error("Connection error while calling E-aggregator API: {}", ex.getMessage());
                    throw new EAggregatorConnectionException("Failed to connect to E-aggregator API: " + ex.getMessage(), ex);
                })
                .doOnError(WebClientResponseException.class, ex -> {
                    // This block is primarily for unhandled HTTP errors not caught by onStatus
                    log.error("HTTP error from E-aggregator API: {} - {}", ex.getStatusCode(), ex.getResponseBodyAsString());
                    throw new EAggregatorApiException(
                            String.format("EAggregator API returned HTTP error: %s - %s", ex.getStatusCode(), ex.getResponseBodyAsString()),
                            ex.getStatusCode().value(),
                            ex.getResponseBodyAsString()
                    );
                })
                .doOnError(Exception.class, ex -> {
                    log.error("An unexpected error occurred during E-aggregator API call: {}", ex.getMessage(), ex);
                    throw new EAggregatorApiException("An unexpected error occurred during E-aggregator API call: " + ex.getMessage(), ex);
                });
    }

    // --- Placeholder DTOs and Custom Exceptions (should be in their own files) ---

    /**
     * Placeholder for EAggregatorOfferRequest DTO.
     * In a real application, this would be a separate class file.
     */
    public static class EAggregatorOfferRequest {
        private String customerId;
        private String productType;
        private Double loanAmount;

        public EAggregatorOfferRequest() {}

        public EAggregatorOfferRequest(String customerId, String productType, Double loanAmount) {
            this.customerId = customerId;
            this.productType = productType;
            this.loanAmount = loanAmount;
        }

        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getProductType() { return productType; }
        public void setProductType(String productType) { this.productType = productType; }
        public Double getLoanAmount() { return loanAmount; }
        public void setLoanAmount(Double loanAmount) { this.loanAmount = loanAmount; }

        @Override
        public String toString() {
            return "EAggregatorOfferRequest{" +
                    "customerId='" + customerId + '\'' +
                    ", productType='" + productType + '\'' +
                    ", loanAmount=" + loanAmount +
                    '}';
        }
    }

    /**
     * Placeholder for EAggregatorOfferResponse DTO.
     * In a real application, this would be a separate class file.
     */
    public static class EAggregatorOfferResponse {
        private String offerId;
        private String customerId;
        private String offerDescription;
        private Double interestRate;
        private String status;

        public EAggregatorOfferResponse() {}

        public EAggregatorOfferResponse(String offerId, String customerId, String offerDescription, Double interestRate, String status) {
            this.offerId = offerId;
            this.customerId = customerId;
            this.offerDescription = offerDescription;
            this.interestRate = interestRate;
            this.status = status;
        }

        public String getOfferId() { return offerId; }
        public void setOfferId(String offerId) { this.offerId = offerId; }
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getOfferDescription() { return offerDescription; }
        public void setOfferDescription(String offerDescription) { this.offerDescription = offerDescription; }
        public Double getInterestRate() { return interestRate; }
        public void setInterestRate(Double interestRate) { this.interestRate = interestRate; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }

        @Override
        public String toString() {
            return "EAggregatorOfferResponse{" +
                    "offerId='" + offerId + '\'' +
                    ", customerId='" + customerId + '\'' +
                    ", offerDescription='" + offerDescription + '\'' +
                    ", interestRate=" + interestRate +
                    ", status='" + status + '\'' +
                    '}';
        }
    }

    /**
     * Custom exception for E-aggregator API related errors (e.g., 4xx/5xx responses).
     * In a real application, this would be a separate class file.
     */
    public static class EAggregatorApiException extends RuntimeException {
        private final int statusCode;
        private final String errorResponse;

        public EAggregatorApiException(String message) {
            super(message);
            this.statusCode = 0; // Default for unknown status
            this.errorResponse = null;
        }

        public EAggregatorApiException(String message, Throwable cause) {
            super(message, cause);
            this.statusCode = 0;
            this.errorResponse = null;
        }

        public EAggregatorApiException(String message, int statusCode, String errorResponse) {
            super(message);
            this.statusCode = statusCode;
            this.errorResponse = errorResponse;
        }

        public int getStatusCode() {
            return statusCode;
        }

        public String getErrorResponse() {
            return errorResponse;
        }
    }

    /**
     * Custom exception for E-aggregator API connection issues (e.g., network down, timeout).
     * In a real application, this would be a separate class file.
     */
    public static class EAggregatorConnectionException extends RuntimeException {
        public EAggregatorConnectionException(String message) {
            super(message);
        }

        public EAggregatorConnectionException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}