package com.ltfs.cdp.integration.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * EAggregatorApiAdapter is a service component responsible for adapting real-time API calls
 * from E-aggregators into internal Customer Data Platform (CDP) data formats.
 * It handles the communication with external E-aggregator systems, converts request/response
 * structures, and manages API-related errors.
 *
 * This adapter acts as a bridge, ensuring that the internal CDP system interacts with
 * E-aggregators using a consistent, adapted data model, abstracting away the external API's
 * specific contract details.
 */
@Service
public class EAggregatorApiAdapter {

    private static final Logger log = LoggerFactory.getLogger(EAggregatorApiAdapter.class);

    private final RestTemplate restTemplate;

    // Configuration properties for the E-aggregator API base URL and specific endpoint
    @Value("${eaggregator.api.base-url}")
    private String eAggregatorBaseUrl;

    @Value("${eaggregator.api.offers-endpoint:/api/v1/customer-offers}")
    private String offersEndpoint;

    /**
     * Constructor for EAggregatorApiAdapter.
     * Spring's dependency injection will provide the RestTemplate instance.
     * It is recommended to configure the RestTemplate (e.g., with timeouts, error handlers)
     * as a bean in a separate configuration class (e.g., WebClientConfig or RestTemplateConfig).
     *
     * @param restTemplate The RestTemplate instance used for making HTTP calls to the E-aggregator API.
     */
    public EAggregatorApiAdapter(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Fetches customer offers from the E-aggregator system based on the provided CDP customer offer request.
     * This method performs the following steps:
     * 1. Converts the internal CDP request format to the E-aggregator's expected request format.
     * 2. Constructs and sends an HTTP POST request to the E-aggregator API.
     * 3. Processes the HTTP response, handling various success and error scenarios.
     * 4. Converts the E-aggregator's response back to the internal CDP offer response format.
     *
     * @param cdpRequest The internal CDP customer offer request containing details like customer ID and product category.
     * @return A {@link CdpCustomerOfferResponse} containing a list of adapted offers.
     *         Returns an empty list of offers within the response if no offers are found or a non-critical error occurs.
     * @throws EAggregatorApiException if a critical or unrecoverable error occurs during the API call or data processing,
     *                                 such as network issues, server errors, or client-side errors from the E-aggregator.
     */
    public CdpCustomerOfferResponse fetchOffersFromEAggregator(CdpCustomerOfferRequest cdpRequest) {
        log.info("Attempting to fetch offers from E-aggregator for customer ID: {}", cdpRequest.getCdpCustomerId());

        // 1. Convert internal CDP request to E-aggregator specific request format
        EAggregatorOfferRequest eAggregatorRequest = toEAggregatorRequest(cdpRequest);
        String apiUrl = eAggregatorBaseUrl + offersEndpoint;

        // Set up HTTP headers, including content type and any required authentication
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        // Example: Add API Key or Bearer Token if required by the E-aggregator API
        // headers.set("X-API-Key", "your-eaggregator-api-key");
        // headers.setBearerAuth("your-bearer-token");

        HttpEntity<EAggregatorOfferRequest> requestEntity = new HttpEntity<>(eAggregatorRequest, headers);

        try {
            // 2. Make the HTTP POST call to the E-aggregator API
            log.debug("Sending request to E-aggregator API: {} with payload: {}", apiUrl, eAggregatorRequest);
            ResponseEntity<EAggregatorOfferResponse> responseEntity = restTemplate.exchange(
                    apiUrl,
                    HttpMethod.POST,
                    requestEntity,
                    EAggregatorOfferResponse.class
            );

            // 3. Process the response based on HTTP status code
            if (responseEntity.getStatusCode().is2xxSuccessful() && responseEntity.getBody() != null) {
                EAggregatorOfferResponse eAggregatorResponse = responseEntity.getBody();
                log.info("Successfully received response from E-aggregator for customer ID: {}. Status: {}",
                        cdpRequest.getCdpCustomerId(), responseEntity.getStatusCode());
                // 4. Convert E-aggregator response to internal CDP response format
                return toCdpResponse(eAggregatorResponse);
            } else {
                // Log non-successful but non-error responses (e.g., 3xx redirects, or 2xx with empty body)
                log.warn("E-aggregator API returned non-successful status code or empty body for customer ID {}: Status {}",
                        cdpRequest.getCdpCustomerId(), responseEntity.getStatusCode());
                // Return an empty response to indicate no offers were retrieved successfully
                return new CdpCustomerOfferResponse(cdpRequest.getCdpCustomerId(), Collections.emptyList());
            }
        } catch (HttpClientErrorException e) {
            // Handle 4xx client errors (e.g., 400 Bad Request, 401 Unauthorized, 404 Not Found)
            log.error("Client error calling E-aggregator API for customer ID {}: Status {} - Body: {}",
                    cdpRequest.getCdpCustomerId(), e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw new EAggregatorApiException("Client error from E-aggregator API: " + e.getMessage(), e.getStatusCode().value(), e);
        } catch (HttpServerErrorException e) {
            // Handle 5xx server errors (e.g., 500 Internal Server Error, 503 Service Unavailable)
            log.error("Server error calling E-aggregator API for customer ID {}: Status {} - Body: {}",
                    cdpRequest.getCdpCustomerId(), e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw new EAggregatorApiException("Server error from E-aggregator API: " + e.getMessage(), e.getStatusCode().value(), e);
        } catch (ResourceAccessException e) {
            // Handle network errors, connection timeouts, DNS issues, etc.
            log.error("Network or communication error accessing E-aggregator API for customer ID {}: {}",
                    cdpRequest.getCdpCustomerId(), e.getMessage(), e);
            throw new EAggregatorApiException("Network error accessing E-aggregator API: " + e.getMessage(), 0, e); // 0 for unknown status
        } catch (Exception e) {
            // Catch any other unexpected exceptions during the API call or response processing
            log.error("An unexpected error occurred while calling E-aggregator API for customer ID {}: {}",
                    cdpRequest.getCdpCustomerId(), e.getMessage(), e);
            throw new EAggregatorApiException("An unexpected error occurred during E-aggregator API call: " + e.getMessage(), -1, e); // -1 for unexpected
        }
    }

    /**
     * Converts an internal CDP customer offer request to an E-aggregator specific request format.
     * This method maps fields from the CDP model to the external E-aggregator model.
     *
     * @param cdpRequest The CDP customer offer request.
     * @return The E-aggregator specific offer request.
     */
    private EAggregatorOfferRequest toEAggregatorRequest(CdpCustomerOfferRequest cdpRequest) {
        // Example mapping: Ensure field names and types match the E-aggregator API contract.
        // Product category mapping is handled by a helper method.
        return new EAggregatorOfferRequest(
                cdpRequest.getCdpCustomerId(),
                mapProductTypeToEAggregatorProduct(cdpRequest.getProductCategory())
        );
    }

    /**
     * Converts an E-aggregator specific offer response to an internal CDP customer offer response.
     * This method iterates through the E-aggregator's offers and maps each one to a CDP offer.
     *
     * @param eAggregatorResponse The E-aggregator specific offer response.
     * @return The internal CDP customer offer response.
     */
    private CdpCustomerOfferResponse toCdpResponse(EAggregatorOfferResponse eAggregatorResponse) {
        if (eAggregatorResponse == null || eAggregatorResponse.getOffers() == null) {
            log.warn("EAggregator response or offers list is null. Returning empty CDP offers.");
            return new CdpCustomerOfferResponse(null, Collections.emptyList());
        }

        // Stream through E-aggregator offers, map them to CDP offers, and collect into a list.
        // Null checks are included to ensure robustness against malformed external responses.
        List<CdpOffer> cdpOffers = eAggregatorResponse.getOffers().stream()
                .filter(Objects::nonNull) // Filter out any null offer details from the external list
                .map(this::mapEAggregatorOfferToCdpOffer)
                .filter(Objects::nonNull) // Filter out any offers that failed mapping (e.g., due to invalid date format)
                .collect(Collectors.toList());

        // The customer ID for the CDP response can be taken from the E-aggregator response
        // if it's included, or from the original request if not.
        String customerId = eAggregatorResponse.getCustomerId();

        return new CdpCustomerOfferResponse(customerId, cdpOffers);
    }

    /**
     * Maps a single E-aggregator offer detail to an internal CDP offer format.
     * This method handles data type conversions (e.g., String date to LocalDate) and null checks
     * for individual offer attributes.
     *
     * @param eAggregatorOfferDetail The E-aggregator offer detail.
     * @return The mapped CDP offer, or null if the input detail is null or critical mapping fails (e.g., unparseable date).
     */
    private CdpOffer mapEAggregatorOfferToCdpOffer(EAggregatorOfferDetail eAggregatorOfferDetail) {
        if (eAggregatorOfferDetail == null) {
            log.warn("Attempted to map a null EAggregatorOfferDetail.");
            return null;
        }

        LocalDate expiryDate = null;
        // Attempt to parse the validity end date string into a LocalDate object
        if (eAggregatorOfferDetail.getValidityEndDate() != null && !eAggregatorOfferDetail.getValidityEndDate().isEmpty()) {
            try {
                // Assuming E-aggregator sends date in "YYYY-MM-DD" format. Adjust format if different.
                expiryDate = LocalDate.parse(eAggregatorOfferDetail.getValidityEndDate());
            } catch (DateTimeParseException e) {
                log.warn("Failed to parse validity end date '{}' from E-aggregator offer ID {}. Proceeding with null expiry date.",
                        eAggregatorOfferDetail.getValidityEndDate(), eAggregatorOfferDetail.getOfferId(), e);
                // In a production scenario, you might decide to throw an exception here,
                // or log and skip this specific offer, depending on business rules.
            }
        }

        return new CdpOffer(
                eAggregatorOfferDetail.getOfferId(),
                eAggregatorOfferDetail.getOfferName(),
                eAggregatorOfferDetail.getLoanAmount(),
                eAggregatorOfferDetail.getInterestRate(),
                expiryDate,
                eAggregatorOfferDetail.getProductCode()
        );
    }

    /**
     * Helper method to map internal CDP product categories to E-aggregator specific product types.
     * This mapping logic is crucial for correct communication with the external system.
     * In a real-world application, this mapping might be driven by configuration, a database,
     * or a dedicated mapping service to allow for dynamic updates.
     *
     * @param cdpProductCategory The internal CDP product category string (e.g., "CONSUMER_LOAN").
     * @return The corresponding E-aggregator product type string (e.g., "CL").
     */
    private String mapProductTypeToEAggregatorProduct(String cdpProductCategory) {
        if (cdpProductCategory == null) {
            log.warn("CDP product category is null. Defaulting to 'UNKNOWN'.");
            return "UNKNOWN";
        }
        // Convert to uppercase for case-insensitive matching
        switch (cdpProductCategory.toUpperCase()) {
            case "CONSUMER_LOAN":
                return "CL";
            case "TOP_UP_LOAN":
                return "TPL";
            case "PRE_APPROVED":
                return "PA";
            case "LOYALTY":
                return "LY";
            // Add more mappings as per E-aggregator's contract
            default:
                log.warn("Unknown CDP product category: {}. Defaulting to 'OTHER' for E-aggregator.", cdpProductCategory);
                return "OTHER";
        }
    }

    // --- Internal CDP Data Transfer Objects (DTOs) ---
    // These DTOs represent the data structures used internally within the CDP system.
    // In a full project, these would typically reside in a separate package like
    // `com.ltfs.cdp.integration.model`. They are included here for self-containment.

    /**
     * Represents the request format for fetching customer offers within the CDP system.
     * This DTO is used when the CDP system initiates a request for offers.
     */
    public static class CdpCustomerOfferRequest {
        private String cdpCustomerId;
        private String productCategory; // e.g., "CONSUMER_LOAN", "TOP_UP_LOAN", "PRE_APPROVED"

        public CdpCustomerOfferRequest() {}

        public CdpCustomerOfferRequest(String cdpCustomerId, String productCategory) {
            this.cdpCustomerId = cdpCustomerId;
            this.productCategory = productCategory;
        }

        public String getCdpCustomerId() {
            return cdpCustomerId;
        }

        public void setCdpCustomerId(String cdpCustomerId) {
            this.cdpCustomerId = cdpCustomerId;
        }

        public String getProductCategory() {
            return productCategory;
        }

        public void setProductCategory(String productCategory) {
            this.productCategory = productCategory;
        }

        @Override
        public String toString() {
            return "CdpCustomerOfferRequest{" +
                    "cdpCustomerId='" + cdpCustomerId + '\'' +
                    ", productCategory='" + productCategory + '\'' +
                    '}';
        }
    }

    /**
     * Represents the response format for customer offers within the CDP system.
     * This DTO is used to encapsulate the offers retrieved and adapted from external systems.
     */
    public static class CdpCustomerOfferResponse {
        private String cdpCustomerId;
        private List<CdpOffer> offers;

        public CdpCustomerOfferResponse() {}

        public CdpCustomerOfferResponse(String cdpCustomerId, List<CdpOffer> offers) {
            this.cdpCustomerId = cdpCustomerId;
            this.offers = offers;
        }

        public String getCdpCustomerId() {
            return cdpCustomerId;
        }

        public void setCdpCustomerId(String cdpCustomerId) {
            this.cdpCustomerId = cdpCustomerId;
        }

        public List<CdpOffer> getOffers() {
            return offers;
        }

        public void setOffers(List<CdpOffer> offers) {
            this.offers = offers;
        }

        @Override
        public String toString() {
            return "CdpCustomerOfferResponse{" +
                    "cdpCustomerId='" + cdpCustomerId + '\'' +
                    ", offers=" + offers +
                    '}';
        }
    }

    /**
     * Represents a single offer entity within the CDP system.
     * This is the standardized format for an offer after adaptation.
     */
    public static class CdpOffer {
        private String offerIdentifier;
        private String offerName;
        private Double loanAmount;
        private Double interestRate;
        private LocalDate expiryDate;
        private String productCode; // Internal product code for the offer

        public CdpOffer() {}

        public CdpOffer(String offerIdentifier, String offerName, Double loanAmount, Double interestRate, LocalDate expiryDate, String productCode) {
            this.offerIdentifier = offerIdentifier;
            this.offerName = offerName;
            this.loanAmount = loanAmount;
            this.interestRate = interestRate;
            this.expiryDate = expiryDate;
            this.productCode = productCode;
        }

        public String getOfferIdentifier() {
            return offerIdentifier;
        }

        public void setOfferIdentifier(String offerIdentifier) {
            this.offerIdentifier = offerIdentifier;
        }

        public String getOfferName() {
            return offerName;
        }

        public void setOfferName(String offerName) {
            this.offerName = offerName;
        }

        public Double getLoanAmount() {
            return loanAmount;
        }

        public void setLoanAmount(Double loanAmount) {
            this.loanAmount = loanAmount;
        }

        public Double getInterestRate() {
            return interestRate;
        }

        public void setInterestRate(Double interestRate) {
            this.interestRate = interestRate;
        }

        public LocalDate getExpiryDate() {
            return expiryDate;
        }

        public void setExpiryDate(LocalDate expiryDate) {
            this.expiryDate = expiryDate;
        }

        public String getProductCode() {
            return productCode;
        }

        public void setProductCode(String productCode) {
            this.productCode = productCode;
        }

        @Override
        public String toString() {
            return "CdpOffer{" +
                    "offerIdentifier='" + offerIdentifier + '\'' +
                    ", offerName='" + offerName + '\'' +
                    ", loanAmount=" + loanAmount +
                    ", interestRate=" + interestRate +
                    ", expiryDate=" + expiryDate +
                    ", productCode='" + productCode + '\'' +
                    '}';
        }
    }

    // --- External E-aggregator API Data Transfer Objects (DTOs) ---
    // These DTOs represent the data structures as defined by the external E-aggregator API.
    // In a full project, these would typically reside in a separate package like
    // `com.ltfs.cdp.integration.external.eaggregator.model`. They are included here for self-containment.

    /**
     * Represents the request format expected by the E-aggregator API.
     * This DTO is used to serialize the request payload sent to the E-aggregator.
     */
    public static class EAggregatorOfferRequest {
        private String customerId;
        private String productType; // e.g., "CL", "TPL", "PA" - specific to E-aggregator's contract

        public EAggregatorOfferRequest() {}

        public EAggregatorOfferRequest(String customerId, String productType) {
            this.customerId = customerId;
            this.productType = productType;
        }

        public String getCustomerId() {
            return customerId;
        }

        public void setCustomerId(String customerId) {
            this.customerId = customerId;
        }

        public String getProductType() {
            return productType;
        }

        public void setProductType(String productType) {
            this.productType = productType;
        }

        @Override
        public String toString() {
            return "EAggregatorOfferRequest{" +
                    "customerId='" + customerId + '\'' +
                    ", productType='" + productType + '\'' +
                    '}';
        }
    }

    /**
     * Represents the top-level response format received from the E-aggregator API.
     * This DTO is used to deserialize the response payload from the E-aggregator.
     */
    public static class EAggregatorOfferResponse {
        private String customerId; // Assuming E-aggregator sends back the customer ID
        private List<EAggregatorOfferDetail> offers;
        private String status; // e.g., "SUCCESS", "FAILED", "NO_OFFERS"
        private String message; // A descriptive message from the E-aggregator

        public EAggregatorOfferResponse() {}

        public EAggregatorOfferResponse(String customerId, List<EAggregatorOfferDetail> offers, String status, String message) {
            this.customerId = customerId;
            this.offers = offers;
            this.status = status;
            this.message = message;
        }

        public String getCustomerId() {
            return customerId;
        }

        public void setCustomerId(String customerId) {
            this.customerId = customerId;
        }

        public List<EAggregatorOfferDetail> getOffers() {
            return offers;
        }

        public void setOffers(List<EAggregatorOfferDetail> offers) {
            this.offers = offers;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public String getMessage() {
            return message;
        }

        public void setMessage(String message) {
            this.message = message;
        }

        @Override
        public String toString() {
            return "EAggregatorOfferResponse{" +
                    "customerId='" + customerId + '\'' +
                    ", offers=" + offers +
                    ", status='" + status + '\'' +
                    ", message='" + message + '\'' +
                    '}';
        }
    }

    /**
     * Represents a single offer detail within the E-aggregator API response.
     * This DTO captures the specific attributes of an offer as provided by the E-aggregator.
     */
    public static class EAggregatorOfferDetail {
        private String offerId;
        private String offerName;
        private Double loanAmount;
        private Double interestRate;
        private String validityEndDate; // Date as String, e.g., "YYYY-MM-DD"
        private String productCode; // E-aggregator's specific product code for this offer

        public EAggregatorOfferDetail() {}

        public EAggregatorOfferDetail(String offerId, String offerName, Double loanAmount, Double interestRate, String validityEndDate, String productCode) {
            this.offerId = offerId;
            this.offerName = offerName;
            this.loanAmount = loanAmount;
            this.interestRate = interestRate;
            this.validityEndDate = validityEndDate;
            this.productCode = productCode;
        }

        public String getOfferId() {
            return offerId;
        }

        public void setOfferId(String offerId) {
            this.offerId = offerId;
        }

        public String getOfferName() {
            return offerName;
        }

        public void setOfferName(String offerName) {
            this.offerName = offerName;
        }

        public Double getLoanAmount() {
            return loanAmount;
        }

        public void setLoanAmount(Double loanAmount) {
            this.loanAmount = loanAmount;
        }

        public Double getInterestRate() {
            return interestRate;
        }

        public void setInterestRate(Double interestRate) {
            this.interestRate = interestRate;
        }

        public String getValidityEndDate() {
            return validityEndDate;
        }

        public void setValidityEndDate(String validityEndDate) {
            this.validityEndDate = validityEndDate;
        }

        public String getProductCode() {
            return productCode;
        }

        public void setProductCode(String productCode) {
            this.productCode = productCode;
        }

        @Override
        public String toString() {
            return "EAggregatorOfferDetail{" +
                    "offerId='" + offerId + '\'' +
                    ", offerName='" + offerName + '\'' +
                    ", loanAmount=" + loanAmount +
                    ", interestRate=" + interestRate +
                    ", validityEndDate='" + validityEndDate + '\'' +
                    ", productCode='" + productCode + '\'' +
                    '}';
        }
    }

    // --- Custom Exception for E-aggregator API errors ---
    // This custom exception provides a structured way to handle and propagate errors
    // specific to the E-aggregator API integration.
    // In a full project, this would typically reside in a separate package like
    // `com.ltfs.cdp.integration.exception`. It is included here for self-containment.

    /**
     * Custom exception for errors encountered during E-aggregator API calls.
     * This exception wraps underlying communication or API-specific errors,
     * providing a consistent error handling mechanism within the CDP integration service.
     */
    public static class EAggregatorApiException extends RuntimeException {
        private final int statusCode;

        /**
         * Constructs a new EAggregatorApiException with the specified detail message,
         * status code, and cause.
         * @param message The detail message (which is saved for later retrieval by the {@link #getMessage()} method).
         * @param statusCode The HTTP status code returned by the E-aggregator API, or a custom code (e.g., 0 for network error, -1 for unexpected).
         * @param cause The cause (which is saved for later retrieval by the {@link #getCause()} method).
         *              (A null value is permitted, and indicates that the cause is nonexistent or unknown.)
         */
        public EAggregatorApiException(String message, int statusCode, Throwable cause) {
            super(message, cause);
            this.statusCode = statusCode;
        }

        /**
         * Constructs a new EAggregatorApiException with the specified detail message and status code.
         * @param message The detail message.
         * @param statusCode The HTTP status code.
         */
        public EAggregatorApiException(String message, int statusCode) {
            super(message);
            this.statusCode = statusCode;
        }

        /**
         * Returns the HTTP status code associated with this exception.
         * @return The status code.
         */
        public int getStatusCode() {
            return statusCode;
        }
    }
}