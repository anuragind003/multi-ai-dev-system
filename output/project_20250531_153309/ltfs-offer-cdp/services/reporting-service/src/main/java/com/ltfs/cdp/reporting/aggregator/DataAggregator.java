package com.ltfs.cdp.reporting.aggregator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * DataAggregator is a core component responsible for aggregating and transforming
 * data from various internal services (Customer Profile, Offer, Campaign)
 * into a unified view suitable for reporting purposes.
 *
 * This component ensures that the reporting data reflects the single customer profile
 * view after deduplication, and enriches it with relevant offer and campaign details.
 * It is designed to be scalable and handle potentially large volumes of data.
 *
 * In a real-world scenario, the mock services and models defined as static nested classes
 * within this file would typically reside in separate files within their respective
 * 'service', 'repository', and 'model' packages, and would interact with other
 * microservices or a database. They are included here for completeness and to make
 * this single file directly runnable for demonstration.
 */
@Service
public class DataAggregator {

    private static final Logger log = LoggerFactory.getLogger(DataAggregator.class);

    private final CustomerProfileService customerProfileService;
    private final OfferService offerService;
    private final CampaignService campaignService;
    private final AggregatedCustomerReportRepository aggregatedCustomerReportRepository;

    /**
     * Constructs a DataAggregator with necessary service and repository dependencies.
     * Spring's dependency injection will automatically provide these beans.
     *
     * @param customerProfileService Service to fetch customer profile data.
     * @param offerService Service to fetch offer data.
     * @param campaignService Service to fetch campaign data.
     * @param aggregatedCustomerReportRepository Repository to persist aggregated report data.
     */
    @Autowired
    public DataAggregator(CustomerProfileService customerProfileService,
                          OfferService offerService,
                          CampaignService campaignService,
                          AggregatedCustomerReportRepository aggregatedCustomerReportRepository) {
        this.customerProfileService = customerProfileService;
        this.offerService = offerService;
        this.campaignService = campaignService;
        this.aggregatedCustomerReportRepository = aggregatedCustomerReportRepository;
    }

    /**
     * Orchestrates the data aggregation process. This method performs the following steps:
     * 1. Fetches all active customer profiles (which are assumed to be already deduplicated).
     * 2. Fetches all offers and groups them by customer ID for efficient lookup.
     * 3. Fetches all campaigns and maps them by campaign ID for efficient lookup.
     * 4. Iterates through each customer profile, building a comprehensive
     *    {@link AggregatedCustomerReport} by combining customer details with their
     *    associated offers and enriching offer data with campaign details.
     * 5. Persists the successfully aggregated reports to the reporting database.
     *
     * This method can be invoked periodically (e.g., via Spring's {@code @Scheduled} annotation)
     * or triggered by an event (e.g., a message from a Kafka topic indicating data updates
     * in source systems).
     *
     * @return A list of {@link AggregatedCustomerReport} objects that were successfully
     *         aggregated and persisted. Returns an empty list if no data is found or
     *         if an error prevents aggregation.
     * @throws RuntimeException if a critical error occurs during the overall aggregation process.
     */
    public List<AggregatedCustomerReport> aggregateAndPersistReportingData() {
        log.info("Starting data aggregation for reporting purposes...");
        List<AggregatedCustomerReport> aggregatedReports = new ArrayList<>();

        try {
            // Step 1: Fetch all active customer profiles (assumed to be deduped)
            List<CustomerProfile> customerProfiles = customerProfileService.getAllCustomerProfiles();
            if (customerProfiles.isEmpty()) {
                log.warn("No customer profiles found for aggregation. Skipping aggregation process.");
                return aggregatedReports;
            }
            log.info("Successfully fetched {} customer profiles.", customerProfiles.size());

            // Step 2: Fetch all offers and group them by customer ID for efficient lookup
            List<OfferData> allOffers = offerService.getAllOffers();
            Map<String, List<OfferData>> offersByCustomerId = allOffers.stream()
                    .collect(Collectors.groupingBy(OfferData::getCustomerId));
            log.info("Successfully fetched {} offers, grouped by customer ID.", allOffers.size());

            // Step 3: Fetch all campaigns and map them by campaign ID for efficient lookup
            List<CampaignData> allCampaigns = campaignService.getAllCampaigns();
            Map<String, CampaignData> campaignsById = allCampaigns.stream()
                    .collect(Collectors.toMap(CampaignData::getCampaignId, campaign -> campaign));
            log.info("Successfully fetched {} campaigns.", allCampaigns.size());

            // Step 4: Process each customer profile to build the aggregated report
            // This loop processes each customer independently, allowing for resilience
            // if aggregation fails for a specific customer.
            for (CustomerProfile customerProfile : customerProfiles) {
                try {
                    // Retrieve offers specific to the current customer
                    List<OfferData> currentCustomerOffers = offersByCustomerId.getOrDefault(customerProfile.getCustomerId(), new ArrayList<>());

                    // Build the aggregated report for the current customer
                    AggregatedCustomerReport report = buildAggregatedReportForCustomer(
                            customerProfile,
                            currentCustomerOffers,
                            campaignsById
                    );
                    aggregatedReports.add(report);
                } catch (Exception e) {
                    // Log the error but continue processing other customers
                    log.error("Error aggregating data for customer ID {}: {}", customerProfile.getCustomerId(), e.getMessage(), e);
                }
            }

            // Step 5: Persist the aggregated reports to the database
            if (!aggregatedReports.isEmpty()) {
                List<AggregatedCustomerReport> savedReports = aggregatedCustomerReportRepository.saveAll(aggregatedReports);
                log.info("Successfully aggregated and persisted {} customer reports.", savedReports.size());
                return savedReports;
            } else {
                log.info("No aggregated reports were generated to persist.");
            }

        } catch (Exception e) {
            // Catch any unexpected critical errors during the overall process
            log.error("Critical error occurred during the data aggregation process: {}", e.getMessage(), e);
            // Re-throw as a runtime exception to indicate a failure in the aggregation job
            throw new RuntimeException("Failed to complete data aggregation due to an unexpected error.", e);
        }
        return aggregatedReports;
    }

    /**
     * Builds a single {@link AggregatedCustomerReport} for a given customer profile.
     * This method combines customer details with their associated offers and enriches
     * offer data with campaign details by looking up campaigns from the provided map.
     *
     * @param customerProfile The deduped customer profile data.
     * @param customerOffers A list of offers specifically associated with this customer.
     * @param campaignsById A map of all campaigns, keyed by campaign ID, for efficient lookup.
     * @return An {@link AggregatedCustomerReport} object containing the combined data for the customer.
     */
    private AggregatedCustomerReport buildAggregatedReportForCustomer(
            CustomerProfile customerProfile,
            List<OfferData> customerOffers,
            Map<String, CampaignData> campaignsById) {

        AggregatedCustomerReport report = new AggregatedCustomerReport();
        // Populate customer-specific fields
        report.setCustomerId(customerProfile.getCustomerId());
        report.setCustomerName(customerProfile.getFullName());
        report.setCustomerEmail(customerProfile.getEmail());
        report.setCustomerMobile(customerProfile.getMobileNumber());
        report.setCustomerPan(customerProfile.getPan());
        report.setCustomerAadhaar(customerProfile.getAadhaar());
        report.setCustomerAddress(customerProfile.getAddress());
        report.setCustomerSegment(customerProfile.getCustomerSegment());
        report.setCustomerStatus(customerProfile.getStatus());
        report.setLastProfileUpdate(customerProfile.getLastUpdated());

        // Transform and enrich offer data
        List<AggregatedCustomerReport.OfferReportDetail> offerReportDetails = customerOffers.stream()
                .map(offer -> {
                    AggregatedCustomerReport.OfferReportDetail offerDetail = new AggregatedCustomerReport.OfferReportDetail();
                    offerDetail.setOfferId(offer.getOfferId());
                    offerDetail.setOfferType(offer.getOfferType());
                    offerDetail.setOfferStatus(offer.getOfferStatus());
                    offerDetail.setOfferAmount(offer.getOfferAmount());
                    offerDetail.setOfferValidityStart(offer.getValidityStartDate());
                    offerDetail.setOfferValidityEnd(offer.getValidityEndDate());
                    offerDetail.setProductType(offer.getProductType());
                    offerDetail.setCampaignId(offer.getCampaignId());

                    // Enrich offer with campaign details using the lookup map
                    Optional.ofNullable(campaignsById.get(offer.getCampaignId()))
                            .ifPresent(campaign -> {
                                offerDetail.setCampaignName(campaign.getCampaignName());
                                offerDetail.setCampaignStartDate(campaign.getStartDate());
                                offerDetail.setCampaignEndDate(campaign.getEndDate());
                                offerDetail.setCampaignDescription(campaign.getDescription());
                            });
                    return offerDetail;
                })
                .collect(Collectors.toList());

        report.setOffers(offerReportDetails);
        report.setTotalOffers(offerReportDetails.size());
        report.setAggregatedAt(LocalDateTime.now()); // Timestamp of when this report was aggregated

        return report;
    }

    // --- Mock/Placeholder Interfaces and Classes for demonstration purposes ---
    // In a production environment, these would be separate files in their respective
    // 'service', 'repository', and 'model' packages, and would typically involve
    // actual database interactions (e.g., Spring Data JPA) or inter-service communication
    // (e.g., REST clients, Kafka consumers).

    /**
     * Placeholder for Customer Profile Service.
     * In a real scenario, this would interact with the Customer Profile microservice
     * to fetch deduped customer data.
     */
    @Service
    public static class CustomerProfileService {
        private static final Logger log = LoggerFactory.getLogger(CustomerProfileService.class);
        /**
         * Simulates fetching all customer profiles from a source system.
         * @return A list of mock customer profiles.
         */
        public List<CustomerProfile> getAllCustomerProfiles() {
            log.debug("Simulating fetching all customer profiles...");
            List<CustomerProfile> profiles = new ArrayList<>();
            profiles.add(new CustomerProfile("CUST001", "John Doe", "john.doe@example.com", "9876543210", "ABCDE1234F", "123456789012", "123 Main St, Anytown", "Premium", "Active", LocalDateTime.now().minusDays(5)));
            profiles.add(new CustomerProfile("CUST002", "Jane Smith", "jane.smith@example.com", "9988776655", "FGHIJ5678K", "234567890123", "456 Oak Ave, Othercity", "Standard", "Active", LocalDateTime.now().minusDays(10)));
            profiles.add(new CustomerProfile("CUST003", "Alice Brown", "alice.brown@example.com", "9123456789", "KLMNO9012L", "345678901234", "789 Pine Rd, Somewhere", "Standard", "Inactive", LocalDateTime.now().minusDays(15)));
            return profiles;
        }
    }

    /**
     * Placeholder for Offer Service.
     * In a real scenario, this would interact with the Offer microservice
     * to fetch offer data.
     */
    @Service
    public static class OfferService {
        private static final Logger log = LoggerFactory.getLogger(OfferService.class);
        /**
         * Simulates fetching all offers from a source system.
         * @return A list of mock offer data.
         */
        public List<OfferData> getAllOffers() {
            log.debug("Simulating fetching all offers...");
            List<OfferData> offers = new ArrayList<>();
            offers.add(new OfferData("OFFER001", "CUST001", "Pre-approved Loan", "Approved", 100000.0, LocalDateTime.now(), LocalDateTime.now().plusMonths(1), "Personal Loan", "CAMP001"));
            offers.add(new OfferData("OFFER002", "CUST001", "Credit Card", "Pending", 50000.0, LocalDateTime.now().minusDays(5), LocalDateTime.now().plusDays(25), "Credit Card", "CAMP002"));
            offers.add(new OfferData("OFFER003", "CUST002", "Top-up Loan", "Approved", 200000.0, LocalDateTime.now().minusDays(10), LocalDateTime.now().plusDays(20), "Home Loan", "CAMP001"));
            offers.add(new OfferData("OFFER004", "CUST002", "Loyalty Bonus", "Claimed", 5000.0, LocalDateTime.now().minusMonths(1), LocalDateTime.now().plusDays(1), "Loyalty", "CAMP003"));
            offers.add(new OfferData("OFFER005", "CUST001", "E-aggregator Offer", "Declined", 75000.0, LocalDateTime.now().minusDays(20), LocalDateTime.now().minusDays(10), "Personal Loan", "CAMP004"));
            return offers;
        }
    }

    /**
     * Placeholder for Campaign Service.
     * In a real scenario, this would interact with the Campaign microservice
     * to fetch campaign details.
     */
    @Service
    public static class CampaignService {
        private static final Logger log = LoggerFactory.getLogger(CampaignService.class);
        /**
         * Simulates fetching all campaigns from a source system.
         * @return A list of mock campaign data.
         */
        public List<CampaignData> getAllCampaigns() {
            log.debug("Simulating fetching all campaigns...");
            List<CampaignData> campaigns = new ArrayList<>();
            campaigns.add(new CampaignData("CAMP001", "Summer Loan Fest", LocalDateTime.now().minusMonths(2), LocalDateTime.now().plusMonths(1), "Special rates for personal and home loans."));
            campaigns.add(new CampaignData("CAMP002", "New Credit Card Launch", LocalDateTime.now().minusDays(15), LocalDateTime.now().plusDays(45), "Exclusive benefits for new credit card applicants."));
            campaigns.add(new CampaignData("CAMP003", "Customer Loyalty Program", LocalDateTime.now().minusYears(1), LocalDateTime.MAX, "Ongoing loyalty rewards for existing customers."));
            campaigns.add(new CampaignData("CAMP004", "Digital Loan Drive", LocalDateTime.now().minusDays(30), LocalDateTime.now().minusDays(5), "Fast and easy digital loan application process."));
            return campaigns;
        }
    }

    /**
     * Placeholder for Aggregated Customer Report Repository.
     * In a real scenario, this would be a Spring Data JPA repository interface
     * interacting with a PostgreSQL database table designed for reporting.
     */
    public interface AggregatedCustomerReportRepository {
        /**
         * Saves all given aggregated reports to the persistent storage.
         * @param reports The list of {@link AggregatedCustomerReport} to save.
         * @return The list of saved reports.
         */
        List<AggregatedCustomerReport> saveAll(List<AggregatedCustomerReport> reports);
        // Additional methods like findById, findAll, etc., would be defined here.
    }

    /**
     * Simple in-memory implementation of AggregatedCustomerReportRepository for demonstration.
     * This stores data in a {@link ConcurrentHashMap} and does not provide actual persistence.
     */
    @Service
    public static class InMemoryAggregatedCustomerReportRepository implements AggregatedCustomerReportRepository {
        private static final Logger log = LoggerFactory.getLogger(InMemoryAggregatedCustomerReportRepository.class);
        // Using a ConcurrentHashMap to simulate a database table where customerId is the primary key
        private final Map<String, AggregatedCustomerReport> store = new ConcurrentHashMap<>();

        /**
         * Simulates saving a list of aggregated reports to an in-memory store.
         * @param reports The list of reports to save.
         * @return The list of reports that were "saved".
         */
        @Override
        public List<AggregatedCustomerReport> saveAll(List<AggregatedCustomerReport> reports) {
            log.debug("Simulating saving {} aggregated reports to in-memory repository...", reports.size());
            reports.forEach(report -> store.put(report.getCustomerId(), report));
            log.debug("Current number of aggregated reports in store: {}", store.size());
            return new ArrayList<>(reports); // Return a copy of the reports that were "saved"
        }
    }

    // --- Data Models (DTOs/POJOs) for demonstration ---
    // These classes represent the data structures used for input from source services
    // and the output aggregated report. In a real project, these would be separate
    // files in a 'model' or 'dto' package.

    /**
     * Represents a deduped customer profile, typically sourced from a Customer 360 or similar service.
     */
    public static class CustomerProfile {
        private String customerId;
        private String fullName;
        private String email;
        private String mobileNumber;
        private String pan;
        private String aadhaar;
        private String address;
        private String customerSegment; // e.g., "Premium", "Standard"
        private String status; // e.g., "Active", "Inactive"
        private LocalDateTime lastUpdated;

        public CustomerProfile(String customerId, String fullName, String email, String mobileNumber, String pan, String aadhaar, String address, String customerSegment, String status, LocalDateTime lastUpdated) {
            this.customerId = customerId;
            this.fullName = fullName;
            this.email = email;
            this.mobileNumber = mobileNumber;
            this.pan = pan;
            this.aadhaar = aadhaar;
            this.address = address;
            this.customerSegment = customerSegment;
            this.status = status;
            this.lastUpdated = lastUpdated;
        }

        // Getters
        public String getCustomerId() { return customerId; }
        public String getFullName() { return fullName; }
        public String getEmail() { return email; }
        public String getMobileNumber() { return mobileNumber; }
        public String getPan() { return pan; }
        public String getAadhaar() { return aadhaar; }
        public String getAddress() { return address; }
        public String getCustomerSegment() { return customerSegment; }
        public String getStatus() { return status; }
        public LocalDateTime getLastUpdated() { return lastUpdated; }
    }

    /**
     * Represents raw offer data, typically sourced from an Offer Management system.
     */
    public static class OfferData {
        private String offerId;
        private String customerId;
        private String offerType; // e.g., "Pre-approved Loan", "Credit Card", "Top-up Loan"
        private String offerStatus; // e.g., "Approved", "Pending", "Declined", "Claimed"
        private Double offerAmount;
        private LocalDateTime validityStartDate;
        private LocalDateTime validityEndDate;
        private String productType; // e.g., "Personal Loan", "Home Loan", "Credit Card"
        private String campaignId; // Link to the campaign that generated this offer

        public OfferData(String offerId, String customerId, String offerType, String offerStatus, Double offerAmount, LocalDateTime validityStartDate, LocalDateTime validityEndDate, String productType, String campaignId) {
            this.offerId = offerId;
            this.customerId = customerId;
            this.offerType = offerType;
            this.offerStatus = offerStatus;
            this.offerAmount = offerAmount;
            this.validityStartDate = validityStartDate;
            this.validityEndDate = validityEndDate;
            this.productType = productType;
            this.campaignId = campaignId;
        }

        // Getters
        public String getOfferId() { return offerId; }
        public String getCustomerId() { return customerId; }
        public String getOfferType() { return offerType; }
        public String getOfferStatus() { return offerStatus; }
        public Double getOfferAmount() { return offerAmount; }
        public LocalDateTime getValidityStartDate() { return validityStartDate; }
        public LocalDateTime getValidityEndDate() { return validityEndDate; }
        public String getProductType() { return productType; }
        public String getCampaignId() { return campaignId; }
    }

    /**
     * Represents raw campaign data, typically sourced from a Campaign Management system.
     */
    public static class CampaignData {
        private String campaignId;
        private String campaignName;
        private LocalDateTime startDate;
        private LocalDateTime endDate;
        private String description;

        public CampaignData(String campaignId, String campaignName, LocalDateTime startDate, LocalDateTime endDate, String description) {
            this.campaignId = campaignId;
            this.campaignName = campaignName;
            this.startDate = startDate;
            this.endDate = endDate;
            this.description = description;
        }

        // Getters
        public String getCampaignId() { return campaignId; }
        public String getCampaignName() { return campaignName; }
        public LocalDateTime getStartDate() { return startDate; }
        public LocalDateTime getEndDate() { return endDate; }
        public String getDescription() { return description; }
    }

    /**
     * Represents the aggregated customer report data. This is a denormalized view
     * designed specifically for reporting and analytical queries. It combines
     * customer profile details with a list of their associated offers,
     * enriched with campaign information.
     * This would typically map to a dedicated table in the reporting database.
     */
    public static class AggregatedCustomerReport {
        private String customerId;
        private String customerName;
        private String customerEmail;
        private String customerMobile;
        private String customerPan;
        private String customerAadhaar;
        private String customerAddress;
        private String customerSegment;
        private String customerStatus;
        private LocalDateTime lastProfileUpdate;
        private List<OfferReportDetail> offers; // List of offers associated with this customer
        private int totalOffers;
        private LocalDateTime aggregatedAt; // Timestamp of when this report was generated

        /**
         * Nested class representing detailed information about an offer within the aggregated report.
         * This includes offer-specific data and relevant campaign details.
         */
        public static class OfferReportDetail {
            private String offerId;
            private String offerType;
            private String offerStatus;
            private Double offerAmount;
            private LocalDateTime offerValidityStart;
            private LocalDateTime offerValidityEnd;
            private String productType;
            private String campaignId;
            private String campaignName;
            private LocalDateTime campaignStartDate;
            private LocalDateTime campaignEndDate;
            private String campaignDescription;

            // Getters and Setters for OfferReportDetail
            public String getOfferId() { return offerId; }
            public void setOfferId(String offerId) { this.offerId = offerId; }
            public String getOfferType() { return offerType; }
            public void setOfferType(String offerType) { this.offerType = offerType; }
            public String getOfferStatus() { return offerStatus; }
            public void setOfferStatus(String offerStatus) { this.offerStatus = offerStatus; }
            public Double getOfferAmount() { return offerAmount; }
            public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }
            public LocalDateTime getOfferValidityStart() { return offerValidityStart; }
            public void setOfferValidityStart(LocalDateTime offerValidityStart) { this.offerValidityStart = offerValidityStart; }
            public LocalDateTime getOfferValidityEnd() { return offerValidityEnd; }
            public void setOfferValidityEnd(LocalDateTime offerValidityEnd) { this.offerValidityEnd = offerValidityEnd; }
            public String getProductType() { return productType; }
            public void setProductType(String productType) { this.productType = productType; }
            public String getCampaignId() { return campaignId; }
            public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
            public String getCampaignName() { return campaignName; }
            public void setCampaignName(String campaignName) { this.campaignName = campaignName; }
            public LocalDateTime getCampaignStartDate() { return campaignStartDate; }
            public void setCampaignStartDate(LocalDateTime campaignStartDate) { this.campaignStartDate = campaignStartDate; }
            public LocalDateTime getCampaignEndDate() { return campaignEndDate; }
            public void setCampaignEndDate(LocalDateTime campaignEndDate) { this.campaignEndDate = campaignEndDate; }
            public String getCampaignDescription() { return campaignDescription; }
            public void setCampaignDescription(String campaignDescription) { this.campaignDescription = campaignDescription; }
        }

        // Getters and Setters for AggregatedCustomerReport
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getCustomerName() { return customerName; }
        public void setCustomerName(String customerName) { this.customerName = customerName; }
        public String getCustomerEmail() { return customerEmail; }
        public void setCustomerEmail(String customerEmail) { this.customerEmail = customerEmail; }
        public String getCustomerMobile() { return customerMobile; }
        public void setCustomerMobile(String customerMobile) { this.customerMobile = customerMobile; }
        public String getCustomerPan() { return customerPan; }
        public void setCustomerPan(String customerPan) { this.customerPan = customerPan; }
        public String getCustomerAadhaar() { return customerAadhaar; }
        public void setCustomerAadhaar(String customerAadhaar) { this.aadhaar = customerAadhaar; }
        public String getCustomerAddress() { return customerAddress; }
        public void setCustomerAddress(String customerAddress) { this.customerAddress = customerAddress; }
        public String getCustomerSegment() { return customerSegment; }
        public void setCustomerSegment(String customerSegment) { this.customerSegment = customerSegment; }
        public String getCustomerStatus() { return customerStatus; }
        public void setCustomerStatus(String customerStatus) { this.customerStatus = customerStatus; }
        public LocalDateTime getLastProfileUpdate() { return lastProfileUpdate; }
        public void setLastProfileUpdate(LocalDateTime lastProfileUpdate) { this.lastProfileUpdate = lastProfileUpdate; }
        public List<OfferReportDetail> getOffers() { return offers; }
        public void setOffers(List<OfferReportDetail> offers) { this.offers = offers; }
        public int getTotalOffers() { return totalOffers; }
        public void setTotalOffers(int totalOffers) { this.totalOffers = totalOffers; }
        public LocalDateTime getAggregatedAt() { return aggregatedAt; }
        public void setAggregatedAt(LocalDateTime aggregatedAt) { this.aggregatedAt = aggregatedAt; }
    }
}