package com.ltfs.cdp.reporting.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * Service class responsible for aggregating data from various microservices
 * (e.g., Customer Service, Offer Service, Campaign Service) to prepare
 * comprehensive reports for the LTFS Offer CDP system.
 * It uses REST API calls to fetch data and leverages asynchronous processing
 * for improved performance when fetching multiple independent data sets.
 *
 * Note: In a real-world project, the DTO classes (CustomerDTO, OfferDTO, CampaignDTO, CustomerReportDTO)
 * would typically reside in separate files within a 'com.ltfs.cdp.reporting.dto' package
 * or a shared 'com.ltfs.cdp.common.dto' module if shared across services.
 * For the purpose of generating a single, complete DataAggregator.java file,
 * they are included here within the same package.
 */
@Service
public class DataAggregator {

    private static final Logger log = LoggerFactory.getLogger(DataAggregator.class);

    private final RestTemplate restTemplate;

    // Configuration properties for external service URLs, with default localhost values for development/testing.
    @Value("${service.customer.url:http://localhost:8081/api/customers}")
    private String customerServiceBaseUrl;

    @Value("${service.offer.url:http://localhost:8082/api/offers}")
    private String offerServiceBaseUrl;

    @Value("${service.campaign.url:http://localhost:8083/api/campaigns}")
    private String campaignServiceBaseUrl;

    /**
     * Constructor for DataAggregator.
     * Spring will automatically inject a configured RestTemplate bean.
     * A RestTemplate bean typically needs to be configured in a Spring Boot application
     * (e.g., via a @Configuration class that returns a new RestTemplate()).
     *
     * @param restTemplate The RestTemplate instance for making HTTP requests to external services.
     */
    public DataAggregator(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Aggregates customer, offer, and campaign data to generate a comprehensive customer report.
     * This method orchestrates calls to various microservices to fetch necessary data.
     * It first fetches customer data synchronously, then all offers related to that customer,
     * and finally asynchronously fetches campaign details for each unique campaign associated with the offers.
     *
     * @param customerId The ID of the customer for whom to generate the report.
     * @return A {@link CustomerReportDTO} containing aggregated data. Returns {@code null} if the customer
     *         is not found or a critical error occurs during the initial customer data fetching.
     */
    public CustomerReportDTO aggregateCustomerReport(String customerId) {
        log.info("Starting data aggregation for customer ID: {}", customerId);

        // 1. Fetch Customer Data - This is a prerequisite, so it's fetched synchronously first.
        CustomerDTO customer = fetchCustomerData(customerId);
        if (customer == null) {
            log.warn("Customer with ID {} not found or an error occurred while fetching customer data. Aborting aggregation.", customerId);
            return null; // Cannot proceed without core customer data
        }

        // 2. Fetch Offers for the Customer - Also critical for the report, even if empty.
        List<OfferDTO> offers = fetchOffersByCustomerId(customerId);
        if (offers.isEmpty()) {
            log.info("No offers found for customer ID: {}. Report will contain customer details only.", customerId);
        }

        // 3. Fetch Campaign Data for each unique campaign ID found in offers.
        // This is done asynchronously using CompletableFuture to improve performance
        // by parallelizing external API calls for independent campaign data.
        Map<String, CompletableFuture<CampaignDTO>> campaignFutures = offers.stream()
                .map(OfferDTO::getCampaignId)
                .distinct() // Ensure we only fetch each campaign once
                .collect(Collectors.toMap(
                        campaignId -> campaignId,
                        this::fetchCampaignDataAsync // Asynchronously fetch campaign data
                ));

        // Wait for all campaign futures to complete and collect results into a map for easy lookup.
        // .join() blocks until the future completes. Errors are caught and logged, returning null for that specific campaign.
        Map<String, CampaignDTO> campaigns = campaignFutures.entrySet().stream()
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        entry -> {
                            try {
                                return entry.getValue().join();
                            } catch (Exception e) {
                                // Log error but allow aggregation to continue for other campaigns/offers
                                log.error("Failed to fetch campaign data for ID {}: {}", entry.getKey(), e.getMessage());
                                return null; // Return null for failed campaign fetches
                            }
                        }
                ));

        // 4. Construct the CustomerReportDTO by combining all fetched data.
        CustomerReportDTO report = new CustomerReportDTO();
        report.setCustomerId(customer.getId());
        report.setCustomerName(customer.getName());
        report.setCustomerEmail(customer.getEmail());
        report.setLoanProducts(customer.getLoanProducts());

        List<CustomerReportDTO.OfferReportDetail> offerDetails = offers.stream()
                .map(offer -> {
                    CustomerReportDTO.OfferReportDetail detail = new CustomerReportDTO.OfferReportDetail();
                    detail.setOfferId(offer.getId());
                    detail.setOfferType(offer.getOfferType());
                    detail.setAmount(offer.getAmount());
                    detail.setStatus(offer.getStatus());

                    // Link offer to its campaign details using the collected campaign map
                    CampaignDTO campaign = campaigns.get(offer.getCampaignId());
                    if (campaign != null) {
                        detail.setCampaignName(campaign.getName());
                        detail.setCampaignStartDate(campaign.getStartDate());
                        detail.setCampaignEndDate(campaign.getEndDate());
                    } else {
                        // Handle cases where campaign data could not be fetched or was null
                        log.warn("Campaign data not found for offer ID {} (Campaign ID: {}). Setting campaign details to N/A.", offer.getId(), offer.getCampaignId());
                        detail.setCampaignName("N/A");
                        detail.setCampaignStartDate(null);
                        detail.setCampaignEndDate(null);
                    }
                    return detail;
                })
                .collect(Collectors.toList());

        report.setOffers(offerDetails);

        log.info("Successfully aggregated data for customer ID: {}", customerId);
        return report;
    }

    /**
     * Fetches customer data from the customer microservice.
     * Handles HTTP client (4xx) and server (5xx) errors, and general exceptions.
     *
     * @param customerId The ID of the customer to fetch.
     * @return {@link CustomerDTO} if found and successfully retrieved, {@code null} otherwise.
     */
    private CustomerDTO fetchCustomerData(String customerId) {
        String url = String.format("%s/%s", customerServiceBaseUrl, customerId);
        try {
            log.debug("Attempting to fetch customer data from: {}", url);
            ResponseEntity<CustomerDTO> response = restTemplate.getForEntity(url, CustomerDTO.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                log.debug("Successfully fetched customer data for ID: {}", customerId);
                return response.getBody();
            } else {
                log.warn("Failed to fetch customer data for ID {}. HTTP Status: {}", customerId, response.getStatusCode());
                return null;
            }
        } catch (HttpClientErrorException e) {
            log.error("Client error fetching customer data for ID {}: Status {} - Body: {}", customerId, e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (HttpServerErrorException e) {
            log.error("Server error fetching customer data for ID {}: Status {} - Body: {}", customerId, e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.error("An unexpected error occurred while fetching customer data for ID {}: {}", customerId, e.getMessage(), e);
            return null;
        }
    }

    /**
     * Fetches a list of offers associated with a specific customer from the offer microservice.
     * Assumes an endpoint that supports filtering by customer ID (e.g., /api/offers?customerId=XYZ).
     *
     * @param customerId The ID of the customer whose offers are to be fetched.
     * @return A {@link List} of {@link OfferDTO}s. Returns an empty list if no offers are found
     *         or if an error occurs during fetching.
     */
    private List<OfferDTO> fetchOffersByCustomerId(String customerId) {
        String url = String.format("%s?customerId=%s", offerServiceBaseUrl, customerId);
        try {
            log.debug("Attempting to fetch offers for customer ID {} from: {}", customerId, url);
            // Using ParameterizedTypeReference to correctly deserialize a List of DTOs from a JSON array.
            ResponseEntity<List<OfferDTO>> response = restTemplate.exchange(
                    url,
                    HttpMethod.GET,
                    null, // No request body for GET
                    new ParameterizedTypeReference<List<OfferDTO>>() {} // Type reference for List<OfferDTO>
            );
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                log.debug("Successfully fetched {} offers for customer ID: {}", response.getBody().size(), customerId);
                return response.getBody();
            } else {
                log.warn("Failed to fetch offers for customer ID {}. HTTP Status: {}", customerId, response.getStatusCode());
                return new ArrayList<>();
            }
        } catch (HttpClientErrorException e) {
            log.error("Client error fetching offers for customer ID {}: Status {} - Body: {}", customerId, e.getStatusCode(), e.getResponseBodyAsString());
            return new ArrayList<>();
        } catch (HttpServerErrorException e) {
            log.error("Server error fetching offers for customer ID {}: Status {} - Body: {}", customerId, e.getStatusCode(), e.getResponseBodyAsString());
            return new ArrayList<>();
        } catch (Exception e) {
            log.error("An unexpected error occurred while fetching offers for customer ID {}: {}", customerId, e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * Asynchronously fetches campaign data from the campaign microservice.
     * This method is designed to be used with {@link CompletableFuture} for parallel execution,
     * allowing multiple campaign fetches to happen concurrently without blocking the main thread.
     *
     * @param campaignId The ID of the campaign to fetch.
     * @return A {@link CompletableFuture} that will eventually hold the {@link CampaignDTO}.
     *         The future will complete with {@code null} if the campaign is not found or an error occurs.
     */
    private CompletableFuture<CampaignDTO> fetchCampaignDataAsync(String campaignId) {
        return CompletableFuture.supplyAsync(() -> {
            String url = String.format("%s/%s", campaignServiceBaseUrl, campaignId);
            try {
                log.debug("Attempting to fetch campaign data from: {}", url);
                ResponseEntity<CampaignDTO> response = restTemplate.getForEntity(url, CampaignDTO.class);
                if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                    log.debug("Successfully fetched campaign data for ID: {}", campaignId);
                    return response.getBody();
                } else {
                    log.warn("Failed to fetch campaign data for ID {}. HTTP Status: {}", campaignId, response.getStatusCode());
                    return null;
                }
            } catch (HttpClientErrorException e) {
                log.error("Client error fetching campaign data for ID {}: Status {} - Body: {}", campaignId, e.getStatusCode(), e.getResponseBodyAsString());
                return null;
            } catch (HttpServerErrorException e) {
                log.error("Server error fetching campaign data for ID {}: Status {} - Body: {}", campaignId, e.getStatusCode(), e.getResponseBodyAsString());
                return null;
            } catch (Exception e) {
                log.error("An unexpected error occurred while fetching campaign data for ID {}: {}", campaignId, e.getMessage(), e);
                return null;
            }
        });
    }
}

/**
 * Data Transfer Object (DTO) representing customer information.
 * Used when fetching data from the Customer Service.
 */
class CustomerDTO {
    private String id;
    private String name;
    private String email;
    private List<String> loanProducts; // e.g., "Loyalty", "Preapproved", "E-aggregator"

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public List<String> getLoanProducts() { return loanProducts; }
    public void setLoanProducts(List<String> loanProducts) { this.loanProducts = loanProducts; }
}

/**
 * Data Transfer Object (DTO) representing offer information.
 * Used when fetching data from the Offer Service.
 */
class OfferDTO {
    private String id;
    private String customerId;
    private String campaignId;
    private String offerType; // e.g., "Top-up", "New Loan"
    private double amount;
    private String status; // e.g., "Active", "Expired", "Accepted"

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public double getAmount() { return amount; }
    public void setAmount(double amount) { this.amount = amount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}

/**
 * Data Transfer Object (DTO) representing campaign information.
 * Used when fetching data from the Campaign Service.
 */
class CampaignDTO {
    private String id;
    private String name;
    private LocalDate startDate;
    private LocalDate endDate;
    private String description;

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}

/**
 * Data Transfer Object (DTO) representing the aggregated customer report.
 * This is the final structure returned by the DataAggregator service, combining
 * customer, offer, and campaign details into a single view.
 */
class CustomerReportDTO {
    private String customerId;
    private String customerName;
    private String customerEmail;
    private List<String> loanProducts;
    private List<OfferReportDetail> offers;

    /**
     * Nested class representing detailed information about an offer within the report.
     * It includes offer-specific details and relevant campaign information.
     */
    public static class OfferReportDetail {
        private String offerId;
        private String offerType;
        private double amount;
        private String status;
        private String campaignName;
        private LocalDate campaignStartDate;
        private LocalDate campaignEndDate;

        // Getters and Setters
        public String getOfferId() { return offerId; }
        public void setOfferId(String offerId) { this.offerId = offerId; }
        public String getOfferType() { return offerType; }
        public void setOfferType(String offerType) { this.offerType = offerType; }
        public double getAmount() { return amount; }
        public void setAmount(double amount) { this.amount = amount; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getCampaignName() { return campaignName; }
        public void setCampaignName(String campaignName) { this.campaignName = campaignName; }
        public LocalDate getCampaignStartDate() { return campaignStartDate; }
        public void setCampaignStartDate(LocalDate campaignStartDate) { this.campaignStartDate = campaignStartDate; }
        public LocalDate getCampaignEndDate() { return campaignEndDate; }
        public void setCampaignEndDate(LocalDate campaignEndDate) { this.campaignEndDate = campaignEndDate; }
    }

    // Getters and Setters for CustomerReportDTO
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public String getCustomerEmail() { return customerEmail; }
    public void setCustomerEmail(String customerEmail) { this.customerEmail = customerEmail; }
    public List<String> getLoanProducts() { return loanProducts; }
    public void setLoanProducts(List<String> loanProducts) { this.loanProducts = loanProducts; }
    public List<OfferReportDetail> getOffers() { return offers; }
    public void setOffers(List<OfferReportDetail> offers) { this.offers = offers; }
}