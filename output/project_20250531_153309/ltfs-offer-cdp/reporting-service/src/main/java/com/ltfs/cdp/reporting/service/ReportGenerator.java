package com.ltfs.cdp.reporting.service;

import com.ltfs.cdp.reporting.dto.DailyDataTallyReportDTO;
import com.ltfs.cdp.reporting.dto.CustomerReportDTO;
import com.ltfs.cdp.reporting.dto.OfferSummaryDTO;
import com.ltfs.cdp.reporting.dto.CampaignSummaryDTO;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.client.CustomerServiceClient;
import com.ltfs.cdp.reporting.client.OfferServiceClient;
import com.ltfs.cdp.reporting.client.CampaignServiceClient;
import com.ltfs.cdp.reporting.model.Customer;
import com.ltfs.cdp.reporting.model.Offer;
import com.ltfs.cdp.reporting.model.Campaign;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class responsible for generating various reports by querying other microservices
 * (Customer, Offer, Campaign) or aggregated data.
 * This class acts as an orchestrator to gather data from different sources and
 * transform it into meaningful reports.
 * <p>
 * It interacts with dedicated service clients to fetch raw data and then processes it
 * into specific report DTOs.
 * </p>
 */
@Service
public class ReportGenerator {

    private static final Logger log = LoggerFactory.getLogger(ReportGenerator.class);

    private final CustomerServiceClient customerServiceClient;
    private final OfferServiceClient offerServiceClient;
    private final CampaignServiceClient campaignServiceClient;

    /**
     * Constructor for ReportGenerator, injecting necessary service clients.
     * Spring's dependency injection automatically provides instances of these clients.
     *
     * @param customerServiceClient Client for interacting with the Customer microservice.
     * @param offerServiceClient    Client for interacting with the Offer microservice.
     * @param campaignServiceClient Client for interacting with the Campaign microservice.
     */
    @Autowired
    public ReportGenerator(CustomerServiceClient customerServiceClient,
                           OfferServiceClient offerServiceClient,
                           CampaignServiceClient campaignServiceClient) {
        this.customerServiceClient = customerServiceClient;
        this.offerServiceClient = offerServiceClient;
        this.campaignServiceClient = campaignServiceClient;
    }

    /**
     * Generates a daily data tally report for a specified date.
     * This report includes counts of new customers, offers, and campaigns created/processed on that day.
     * It queries each respective microservice client for the counts.
     *
     * @param date The date for which the report is to be generated.
     * @return A {@link DailyDataTallyReportDTO} containing the counts for the specified date.
     * @throws ReportGenerationException if an error occurs during data retrieval from external services
     *                                   or during report aggregation.
     */
    public DailyDataTallyReportDTO generateDailyDataTallyReport(LocalDate date) {
        log.info("Attempting to generate daily data tally report for date: {}", date);
        try {
            // Fetch counts from respective services. These calls would typically be
            // synchronous REST calls to other microservices (e.g., using Spring's WebClient or RestTemplate).
            long newCustomersCount = customerServiceClient.countCustomersCreatedOn(date);
            long newOffersCount = offerServiceClient.countOffersCreatedOn(date);
            long newCampaignsCount = campaignServiceClient.countCampaignsCreatedOn(date);

            DailyDataTallyReportDTO report = new DailyDataTallyReportDTO(
                date,
                newCustomersCount,
                newOffersCount,
                newCampaignsCount
            );
            log.info("Successfully generated daily data tally report for date {}: {}", date, report);
            return report;
        } catch (Exception e) {
            // Catching a general Exception to handle potential issues from client calls (e.g., network errors,
            // service unavailability, deserialization errors).
            log.error("Error generating daily data tally report for date {}: {}", date, e.getMessage(), e);
            throw new ReportGenerationException("Failed to generate daily data tally report for " + date, e);
        }
    }

    /**
     * Generates a comprehensive customer-level view report for a given customer ID.
     * This report includes the customer's profile details, a summary of all offers associated with them,
     * and a summary of all campaigns they are part of.
     * It orchestrates calls to the Customer, Offer, and Campaign microservices.
     *
     * @param customerId The unique identifier of the customer for whom the report is to be generated.
     * @return An {@link Optional} containing {@link CustomerReportDTO} if the customer is found and
     *         the report can be generated; otherwise, an empty Optional if the customer does not exist.
     * @throws ReportGenerationException if an error occurs during data retrieval from external services
     *                                   or during report aggregation.
     */
    public Optional<CustomerReportDTO> generateCustomerLevelViewReport(String customerId) {
        log.info("Attempting to generate customer-level view report for customer ID: {}", customerId);
        try {
            // 1. Fetch customer details from the Customer microservice.
            Optional<Customer> customerOptional = customerServiceClient.getCustomerById(customerId);

            // If customer is not found, return empty Optional as there's no report to generate.
            if (customerOptional.isEmpty()) {
                log.warn("Customer with ID {} not found. Cannot generate customer-level report.", customerId);
                return Optional.empty();
            }

            Customer customer = customerOptional.get();

            // 2. Fetch offers associated with the customer from the Offer microservice.
            // If no offers are found, an empty list is returned, which is handled gracefully.
            List<Offer> offers = offerServiceClient.getOffersByCustomerId(customerId);
            List<OfferSummaryDTO> offerSummaries = offers.stream()
                .map(this::mapToOfferSummaryDTO) // Map Offer entities to simplified DTOs
                .collect(Collectors.toList());

            // 3. Fetch campaigns associated with the customer from the Campaign microservice.
            // This assumes the Campaign service has a direct way to link campaigns to customers.
            List<Campaign> campaigns = campaignServiceClient.getCampaignsByCustomerId(customerId);
            List<CampaignSummaryDTO> campaignSummaries = campaigns.stream()
                .map(this::mapToCampaignSummaryDTO) // Map Campaign entities to simplified DTOs
                .collect(Collectors.toList());

            // 4. Assemble the final CustomerReportDTO.
            CustomerReportDTO report = new CustomerReportDTO(
                customer.getId(),
                customer.getFirstName(),
                customer.getLastName(),
                customer.getEmail(),
                customer.getPhoneNumber(),
                offerSummaries,
                campaignSummaries
            );
            log.info("Successfully generated customer-level view report for customer ID: {}", customerId);
            return Optional.of(report);

        } catch (Exception e) {
            // Catching a general Exception to handle potential issues from client calls.
            log.error("Error generating customer-level view report for customer ID {}: {}", customerId, e.getMessage(), e);
            throw new ReportGenerationException("Failed to generate customer-level view report for customer ID " + customerId, e);
        }
    }

    /**
     * Helper method to map an {@link Offer} entity (received from Offer microservice)
     * to an {@link OfferSummaryDTO} for reporting purposes.
     * In a larger, more complex application, a dedicated mapping library like MapStruct
     * would typically be used for such transformations.
     *
     * @param offer The {@link Offer} entity to be mapped.
     * @return The corresponding {@link OfferSummaryDTO}.
     */
    private OfferSummaryDTO mapToOfferSummaryDTO(Offer offer) {
        return new OfferSummaryDTO(
            offer.getOfferId(),
            offer.getOfferName(),
            offer.getOfferType(),
            offer.getAmount(),
            offer.getStatus(),
            offer.getCreationDate()
        );
    }

    /**
     * Helper method to map a {@link Campaign} entity (received from Campaign microservice)
     * to a {@link CampaignSummaryDTO} for reporting purposes.
     * Similar to {@code mapToOfferSummaryDTO}, this would ideally be handled by a mapping library.
     *
     * @param campaign The {@link Campaign} entity to be mapped.
     * @return The corresponding {@link CampaignSummaryDTO}.
     */
    private CampaignSummaryDTO mapToCampaignSummaryDTO(Campaign campaign) {
        return new CampaignSummaryDTO(
            campaign.getCampaignId(),
            campaign.getCampaignName(),
            campaign.getStartDate(),
            campaign.getEndDate(),
            campaign.getStatus()
        );
    }
}

// --- Placeholder Interfaces/Classes for Compilation ---
// In a real Spring Boot project, these classes/interfaces would reside in separate files
// within their respective packages (e.g., com.ltfs.cdp.reporting.dto,
// com.ltfs.cdp.reporting.model, com.ltfs.cdp.reporting.client, com.ltfs.cdp.reporting.exception).
// They are included here to make this single file directly runnable and compilable.

/**
 * DTO for the Daily Data Tally Report.
 * Represents aggregated counts of new customers, offers, and campaigns for a specific date.
 */
class DailyDataTallyReportDTO {
    private final LocalDate date;
    private final long newCustomersCount;
    private final long newOffersCount;
    private final long newCampaignsCount;

    public DailyDataTallyReportDTO(LocalDate date, long newCustomersCount, long newOffersCount, long newCampaignsCount) {
        this.date = date;
        this.newCustomersCount = newCustomersCount;
        this.newOffersCount = newOffersCount;
        this.newCampaignsCount = newCampaignsCount;
    }

    public LocalDate getDate() { return date; }
    public long getNewCustomersCount() { return newCustomersCount; }
    public long getNewOffersCount() { return newOffersCount; }
    public long getNewCampaignsCount() { return newCampaignsCount; }

    @Override
    public String toString() {
        return "DailyDataTallyReportDTO{" +
               "date=" + date +
               ", newCustomersCount=" + newCustomersCount +
               ", newOffersCount=" + newOffersCount +
               ", newCampaignsCount=" + newCampaignsCount +
               '}';
    }
}

/**
 * DTO for a comprehensive Customer-Level View Report.
 * Contains core customer details along with summaries of associated offers and campaigns.
 */
class CustomerReportDTO {
    private final String customerId;
    private final String firstName;
    private final String lastName;
    private final String email;
    private final String phoneNumber;
    private final List<OfferSummaryDTO> offers;
    private final List<CampaignSummaryDTO> campaigns;

    public CustomerReportDTO(String customerId, String firstName, String lastName, String email, String phoneNumber,
                             List<OfferSummaryDTO> offers, List<CampaignSummaryDTO> campaigns) {
        this.customerId = customerId;
        this.firstName = firstName;
        this.lastName = lastName;
        this.email = email;
        this.phoneNumber = phoneNumber;
        this.offers = offers != null ? offers : Collections.emptyList();
        this.campaigns = campaigns != null ? campaigns : Collections.emptyList();
    }

    public String getCustomerId() { return customerId; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getEmail() { return email; }
    public String getPhoneNumber() { return phoneNumber; }
    public List<OfferSummaryDTO> getOffers() { return offers; }
    public List<CampaignSummaryDTO> getCampaigns() { return campaigns; }
}

/**
 * DTO for a summarized view of an Offer, used within reports.
 */
class OfferSummaryDTO {
    private final String offerId;
    private final String offerName;
    private final String offerType;
    private final double amount;
    private final String status;
    private final LocalDate creationDate;

    public OfferSummaryDTO(String offerId, String offerName, String offerType, double amount, String status, LocalDate creationDate) {
        this.offerId = offerId;
        this.offerName = offerName;
        this.offerType = offerType;
        this.amount = amount;
        this.status = status;
        this.creationDate = creationDate;
    }

    public String getOfferId() { return offerId; }
    public String getOfferName() { return offerName; }
    public String getOfferType() { return offerType; }
    public double getAmount() { return amount; }
    public String getStatus() { return status; }
    public LocalDate getCreationDate() { return creationDate; }
}

/**
 * DTO for a summarized view of a Campaign, used within reports.
 */
class CampaignSummaryDTO {
    private final String campaignId;
    private final String campaignName;
    private final LocalDate startDate;
    private final LocalDate endDate;
    private final String status;

    public CampaignSummaryDTO(String campaignId, String campaignName, LocalDate startDate, LocalDate endDate, String status) {
        this.campaignId = campaignId;
        this.campaignName = campaignName;
        this.startDate = startDate;
        this.endDate = endDate;
        this.status = status;
    }

    public String getCampaignId() { return campaignId; }
    public String getCampaignName() { return campaignName; }
    public LocalDate getStartDate() { return startDate; }
    public LocalDate getEndDate() { return endDate; }
    public String getStatus() { return status; }
}

/**
 * Simplified model representing a Customer entity, typically fetched from the Customer microservice.
 */
class Customer {
    private final String id;
    private final String firstName;
    private final String lastName;
    private final String email;
    private final String phoneNumber;
    private final LocalDate creationDate;

    public Customer(String id, String firstName, String lastName, String email, String phoneNumber, LocalDate creationDate) {
        this.id = id;
        this.firstName = firstName;
        this.lastName = lastName;
        this.email = email;
        this.phoneNumber = phoneNumber;
        this.creationDate = creationDate;
    }

    public String getId() { return id; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getEmail() { return email; }
    public String getPhoneNumber() { return phoneNumber; }
    public LocalDate getCreationDate() { return creationDate; }
}

/**
 * Simplified model representing an Offer entity, typically fetched from the Offer microservice.
 */
class Offer {
    private final String offerId;
    private final String offerName;
    private final String offerType;
    private final double amount;
    private final String status;
    private final String customerId; // Link to customer
    private final LocalDate creationDate;

    public Offer(String offerId, String offerName, String offerType, double amount, String status, String customerId, LocalDate creationDate) {
        this.offerId = offerId;
        this.offerName = offerName;
        this.offerType = offerType;
        this.amount = amount;
        this.status = status;
        this.customerId = customerId;
        this.creationDate = creationDate;
    }

    public String getOfferId() { return offerId; }
    public String getOfferName() { return offerName; }
    public String getOfferType() { return offerType; }
    public double getAmount() { return amount; }
    public String getStatus() { return status; }
    public String getCustomerId() { return customerId; }
    public LocalDate getCreationDate() { return creationDate; }
}

/**
 * Simplified model representing a Campaign entity, typically fetched from the Campaign microservice.
 */
class Campaign {
    private final String campaignId;
    private final String campaignName;
    private final LocalDate startDate;
    private final LocalDate endDate;
    private final String status;

    public Campaign(String campaignId, String campaignName, LocalDate startDate, LocalDate endDate, String status) {
        this.campaignId = campaignId;
        this.campaignName = campaignName;
        this.startDate = startDate;
        this.endDate = endDate;
        this.status = status;
    }

    public String getCampaignId() { return campaignId; }
    public String getCampaignName() { return campaignName; }
    public LocalDate getStartDate() { return startDate; }
    public LocalDate getEndDate() { return endDate; }
    public String getStatus() { return status; }
}

/**
 * Client interface for interacting with the Customer microservice.
 * In a real application, this would be implemented using FeignClient, WebClient, or RestTemplate.
 */
interface CustomerServiceClient {
    /**
     * Counts the number of customers created on a specific date.
     * @param date The date to count customers for.
     * @return The count of customers.
     */
    long countCustomersCreatedOn(LocalDate date);

    /**
     * Retrieves a customer by their unique ID.
     * @param customerId The ID of the customer.
     * @return An Optional containing the Customer if found, otherwise empty.
     */
    Optional<Customer> getCustomerById(String customerId);
}

/**
 * Client interface for interacting with the Offer microservice.
 * In a real application, this would be implemented using FeignClient, WebClient, or RestTemplate.
 */
interface OfferServiceClient {
    /**
     * Counts the number of offers created on a specific date.
     * @param date The date to count offers for.
     * @return The count of offers.
     */
    long countOffersCreatedOn(LocalDate date);

    /**
     * Retrieves all offers associated with a specific customer ID.
     * @param customerId The ID of the customer.
     * @return A list of offers, or an empty list if none are found.
     */
    List<Offer> getOffersByCustomerId(String customerId);
}

/**
 * Client interface for interacting with the Campaign microservice.
 * In a real application, this would be implemented using FeignClient, WebClient, or RestTemplate.
 */
interface CampaignServiceClient {
    /**
     * Counts the number of campaigns created on a specific date.
     * @param date The date to count campaigns for.
     * @return The count of campaigns.
     */
    long countCampaignsCreatedOn(LocalDate date);

    /**
     * Retrieves all campaigns associated with a specific customer ID.
     * This method assumes a direct link between customers and campaigns in the Campaign service.
     * @param customerId The ID of the customer.
     * @return A list of campaigns, or an empty list if none are found.
     */
    List<Campaign> getCampaignsByCustomerId(String customerId);
}

/**
 * Custom runtime exception for errors occurring during report generation.
 * This allows for specific error handling related to reporting failures.
 */
class ReportGenerationException extends RuntimeException {
    public ReportGenerationException(String message) {
        super(message);
    }

    public ReportGenerationException(String message, Throwable cause) {
        super(message, cause);
    }
}