package com.ltfs.cdp.integration.offermart;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.scheduling.annotation.Scheduled; // Potentially for scheduled ingestion

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

// --- Placeholder DTOs (In a real project, these would typically reside in a 'model' or 'dto' package) ---

/**
 * Data Transfer Object (DTO) for customer data received from the Offermart system.
 * This class represents the raw structure of customer records as they are ingested,
 * before any extensive transformation or mapping to internal CDP entities.
 * It includes fields relevant for customer profiling and deduplication.
 */
class OffermartCustomerDTO {
    private String customerId;
    private String firstName;
    private String lastName;
    private String pan; // Permanent Account Number, crucial for deduplication
    private String mobileNumber; // Mobile number, crucial for deduplication
    private String email;
    private LocalDate dateOfBirth;

    /**
     * Default constructor.
     */
    public OffermartCustomerDTO() {
    }

    /**
     * Parameterized constructor for creating an OffermartCustomerDTO instance.
     *
     * @param customerId   Unique identifier for the customer from Offermart.
     * @param firstName    Customer's first name.
     * @param lastName     Customer's last name.
     * @param pan          Customer's PAN.
     * @param mobileNumber Customer's mobile number.
     * @param email        Customer's email address.
     * @param dateOfBirth  Customer's date of birth.
     */
    public OffermartCustomerDTO(String customerId, String firstName, String lastName, String pan, String mobileNumber, String email, LocalDate dateOfBirth) {
        this.customerId = customerId;
        this.firstName = firstName;
        this.lastName = lastName;
        this.pan = pan;
        this.mobileNumber = mobileNumber;
        this.email = email;
        this.dateOfBirth = dateOfBirth;
    }

    // Getters
    public String getCustomerId() {
        return customerId;
    }

    public String getFirstName() {
        return firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public String getPan() {
        return pan;
    }

    public String getMobileNumber() {
        return mobileNumber;
    }

    public String getEmail() {
        return email;
    }

    public LocalDate getDateOfBirth() {
        return dateOfBirth;
    }

    // Setters
    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public void setPan(String pan) {
        this.pan = pan;
    }

    public void setMobileNumber(String mobileNumber) {
        this.mobileNumber = mobileNumber;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public void setDateOfBirth(LocalDate dateOfBirth) {
        this.dateOfBirth = dateOfBirth;
    }

    /**
     * Provides a string representation of the DTO, masking sensitive information for logging.
     *
     * @return A string representation of the OffermartCustomerDTO.
     */
    @Override
    public String toString() {
        return "OffermartCustomerDTO{" +
                "customerId='" + customerId + '\'' +
                ", firstName='" + firstName + '\'' +
                ", lastName='" + lastName + '\'' +
                ", pan='" + (pan != null ? pan.substring(0, Math.min(pan.length(), 4)) + "..." : "null") + '\'' + // Mask PAN
                ", mobileNumber='" + (mobileNumber != null ? mobileNumber.substring(0, Math.min(mobileNumber.length(), 4)) + "..." : "null") + '\'' + // Mask mobile
                '}';
    }
}

/**
 * Data Transfer Object (DTO) for offer data received from the Offermart system.
 * This class represents the raw structure of offer records as they are ingested,
 * before any extensive transformation or mapping to internal CDP entities.
 * It includes fields relevant for offer management and offer-specific deduplication.
 */
class OffermartOfferDTO {
    private String offerId;
    private String customerId; // Link to the customer associated with this offer
    private String loanType; // e.g., "Loyalty", "Preapproved", "E-aggregator", "Top-up"
    private double offerAmount;
    private String campaignId;
    private LocalDate offerDate;
    private LocalDate expiryDate;

    /**
     * Default constructor.
     */
    public OffermartOfferDTO() {
    }

    /**
     * Parameterized constructor for creating an OffermartOfferDTO instance.
     *
     * @param offerId     Unique identifier for the offer from Offermart.
     * @param customerId  The ID of the customer to whom this offer is made.
     * @param loanType    The type of loan product (e.g., "Top-up", "Preapproved").
     * @param offerAmount The monetary amount of the offer.
     * @param campaignId  The ID of the campaign associated with this offer.
     * @param offerDate   The date the offer was generated.
     * @param expiryDate  The date the offer expires.
     */
    public OffermartOfferDTO(String offerId, String customerId, String loanType, double offerAmount, String campaignId, LocalDate offerDate, LocalDate expiryDate) {
        this.offerId = offerId;
        this.customerId = customerId;
        this.loanType = loanType;
        this.offerAmount = offerAmount;
        this.campaignId = campaignId;
        this.offerDate = offerDate;
        this.expiryDate = expiryDate;
    }

    // Getters
    public String getOfferId() {
        return offerId;
    }

    public String getCustomerId() {
        return customerId;
    }

    public String getLoanType() {
        return loanType;
    }

    public double getOfferAmount() {
        return offerAmount;
    }

    public String getCampaignId() {
        return campaignId;
    }

    public LocalDate getOfferDate() {
        return offerDate;
    }

    public LocalDate getExpiryDate() {
        return expiryDate;
    }

    // Setters
    public void setOfferId(String offerId) {
        this.offerId = offerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public void setLoanType(String loanType) {
        this.loanType = loanType;
    }

    public void setOfferAmount(double offerAmount) {
        this.offerAmount = offerAmount;
    }

    public void setCampaignId(String campaignId) {
        this.campaignId = campaignId;
    }

    public void setOfferDate(LocalDate offerDate) {
        this.offerDate = offerDate;
    }

    public void setExpiryDate(LocalDate expiryDate) {
        this.expiryDate = expiryDate;
    }

    /**
     * Provides a string representation of the DTO.
     *
     * @return A string representation of the OffermartOfferDTO.
     */
    @Override
    public String toString() {
        return "OffermartOfferDTO{" +
                "offerId='" + offerId + '\'' +
                ", customerId='" + customerId + '\'' +
                ", loanType='" + loanType + '\'' +
                ", offerAmount=" + offerAmount +
                ", campaignId='" + campaignId + '\'' +
                '}';
    }
}

// --- Placeholder Service Interface and Implementation (In a real project, these would be in 'service' and 'service.impl' packages) ---

/**
 * Service interface for processing Offermart data.
 * Defines the contract for ingesting customer and offer data,
 * which includes validation, transformation, and triggering deduplication.
 */
interface OffermartIngestionService {
    /**
     * Ingests a batch of customer data received from Offermart.
     * This method is responsible for orchestrating the validation,
     * mapping to internal entities, triggering deduplication, and persistence.
     *
     * @param customerData A list of {@link OffermartCustomerDTO} representing raw customer records.
     */
    void ingestCustomerData(List<OffermartCustomerDTO> customerData);

    /**
     * Ingests a batch of offer data received from Offermart.
     * This method is responsible for orchestrating the validation,
     * mapping to internal entities, triggering offer-specific deduplication, and persistence.
     *
     * @param offerData A list of {@link OffermartOfferDTO} representing raw offer records.
     */
    void ingestOfferData(List<OffermartOfferDTO> offerData);
}

/**
 * Concrete implementation of {@link OffermartIngestionService}.
 * This service handles the core business logic for processing Offermart data.
 * In a real application, this would interact with repositories, dedicated validation components,
 * and deduplication services (e.g., CustomerDeduplicationService, OfferDeduplicationService).
 */
@Service
class OffermartIngestionServiceImpl implements OffermartIngestionService {
    private static final Logger log = LoggerFactory.getLogger(OffermartIngestionServiceImpl.class);

    /**
     * Processes a list of Offermart customer DTOs.
     * This method would typically:
     * 1. Perform basic column-level validation on data moving from Offermart to CDP System.
     * 2. Map DTOs to internal Customer entities (e.g., {@code com.ltfs.cdp.core.model.Customer}).
     * 3. Apply dedupe logic across all Consumer Loan (CL) products (Loyalty, Preapproved, E-aggregator etc.).
     * 4. Perform deduplication against the 'live book' (Customer 360) before offers are finalized.
     * 5. Persist valid and deduped customer data into the CDP.
     *
     * @param customerData List of customer DTOs from Offermart.
     */
    @Override
    public void ingestCustomerData(List<OffermartCustomerDTO> customerData) {
        if (customerData == null || customerData.isEmpty()) {
            log.info("No customer records provided for ingestion from Offermart.");
            return;
        }
        log.info("Starting ingestion of {} customer records from Offermart.", customerData.size());

        List<OffermartCustomerDTO> validCustomers = new ArrayList<>();
        for (OffermartCustomerDTO customer : customerData) {
            // Perform basic column-level validation as per functional requirements
            if (customer.getCustomerId() == null || customer.getCustomerId().trim().isEmpty()) {
                log.warn("Validation failed: Skipping customer record due to missing Customer ID. Record: {}", customer);
                continue;
            }
            if (customer.getMobileNumber() == null || customer.getMobileNumber().trim().isEmpty()) {
                log.warn("Validation failed: Skipping customer record {} due to missing Mobile Number.", customer.getCustomerId());
                continue;
            }
            if (customer.getPan() == null || customer.getPan().trim().isEmpty()) {
                log.warn("Validation failed: Skipping customer record {} due to missing PAN.", customer.getCustomerId());
                continue;
            }
            // Add more validation rules (e.g., format checks for PAN, mobile, email, date of birth)
            validCustomers.add(customer);
        }

        log.info("Successfully validated {} customer records. Proceeding with deduplication and persistence.", validCustomers.size());

        // In a real scenario, this would involve:
        // 1. Mapping `validCustomers` (OffermartCustomerDTO) to internal Customer entities (e.g., Customer.java).
        //    This might involve data type conversions, default value assignments, etc.
        // 2. Calling a dedicated CustomerDeduplicationService:
        //    `customerDeduplicationService.deduplicateAndPersist(mappedCustomers);`
        //    This service would implement the complex deduplication logic:
        //    - Comparing new customer data against the 'live book' (Customer 360).
        //    - Applying dedupe logic across all Consumer Loan (CL) products (Loyalty, Preapproved, E-aggregator etc.).
        //    - Merging duplicate profiles or updating existing ones.
        //    - Persisting the final, deduped customer profile to the PostgreSQL database.
        validCustomers.forEach(customer -> log.debug("Simulating processing for customer: {}", customer.getCustomerId()));
        log.info("Customer data ingestion from Offermart completed for {} valid records.", validCustomers.size());
    }

    /**
     * Processes a list of Offermart offer DTOs.
     * This method would typically:
     * 1. Perform basic column-level validation on data moving from Offermart to CDP System.
     * 2. Map DTOs to internal Offer entities (e.g., {@code com.ltfs.cdp.core.model.Offer}).
     * 3. Apply offer-specific deduplication logic (e.g., Top-up loans).
     * 4. Persist valid and deduped offer data into the CDP.
     *
     * @param offerData List of offer DTOs from Offermart.
     */
    @Override
    public void ingestOfferData(List<OffermartOfferDTO> offerData) {
        if (offerData == null || offerData.isEmpty()) {
            log.info("No offer records provided for ingestion from Offermart.");
            return;
        }
        log.info("Starting ingestion of {} offer records from Offermart.", offerData.size());

        List<OffermartOfferDTO> validOffers = new ArrayList<>();
        for (OffermartOfferDTO offer : offerData) {
            // Perform basic column-level validation as per functional requirements
            if (offer.getOfferId() == null || offer.getOfferId().trim().isEmpty()) {
                log.warn("Validation failed: Skipping offer record due to missing Offer ID. Record: {}", offer);
                continue;
            }
            if (offer.getCustomerId() == null || offer.getCustomerId().trim().isEmpty()) {
                log.warn("Validation failed: Skipping offer record {} due to missing Customer ID.", offer.getOfferId());
                continue;
            }
            if (offer.getOfferAmount() <= 0) {
                log.warn("Validation failed: Skipping offer record {} due to invalid offer amount: {}. Offer must be positive.", offer.getOfferId(), offer.getOfferAmount());
                continue;
            }
            if (offer.getLoanType() == null || offer.getLoanType().trim().isEmpty()) {
                log.warn("Validation failed: Skipping offer record {} due to missing Loan Type.", offer.getOfferId());
                continue;
            }
            // Add more validation rules (e.g., date validity, campaign ID existence)
            validOffers.add(offer);
        }

        log.info("Successfully validated {} offer records. Proceeding with offer-specific deduplication and persistence.", validOffers.size());

        // In a real scenario, this would involve:
        // 1. Mapping `validOffers` (OffermartOfferDTO) to internal Offer entities (e.g., Offer.java).
        // 2. Calling a dedicated OfferDeduplicationService:
        //    `offerDeduplicationService.deduplicateAndPersist(mappedOffers);`
        //    This service would implement the offer-specific deduplication logic:
        //    - Top-up loan offers must be deduped only within other Top-up offers.
        //    - Matches found should be removed or flagged as duplicates.
        //    - Persisting the final, deduped offer data to the PostgreSQL database.
        validOffers.forEach(offer -> log.debug("Simulating processing for offer: {}", offer.getOfferId()));
        log.info("Offer data ingestion from Offermart completed for {} valid records.", validOffers.size());
    }
}

/**
 * {@code OffermartDataIngestor} is a Spring service component responsible for
 * orchestrating the batch ingestion of customer and offer data from the Offermart system
 * into the CDP (Customer Data Platform).
 *
 * This class acts as an entry point for the ingestion process, simulating data retrieval
 * from Offermart and delegating the actual processing (validation, deduplication, persistence)
 * to the {@link OffermartIngestionService}.
 *
 * The ingestion process can be triggered manually, via a scheduled task, or by an event.
 */
@Service
public class OffermartDataIngestor {

    private static final Logger log = LoggerFactory.getLogger(OffermartDataIngestor.class);

    private final OffermartIngestionService offermartIngestionService;

    /**
     * Constructs an {@code OffermartDataIngestor} with the necessary dependencies.
     * Spring's dependency injection automatically provides the {@link OffermartIngestionService} instance.
     *
     * @param offermartIngestionService The service responsible for processing ingested Offermart data.
     */
    @Autowired
    public OffermartDataIngestor(OffermartIngestionService offermartIngestionService) {
        this.offermartIngestionService = offermartIngestionService;
    }

    /**
     * Initiates the batch ingestion process for customer and offer data from Offermart.
     * This method simulates fetching data from Offermart and then passes it to the
     * {@link OffermartIngestionService} for further processing.
     *
     * In a production environment, this method might be triggered by:
     * - A cron job using {@code @Scheduled} for periodic batch runs.
     * - A message from a queue (e.g., Kafka, RabbitMQ) indicating new data is available.
     * - A REST API endpoint call for on-demand ingestion.
     *
     * For demonstration purposes, data retrieval is simulated using dummy data.
     */
    // Example of a scheduled task. Uncomment and configure cron expression as needed.
    // The cron expression "0 0 2 * * ?" means 2 AM every day.
    // @Scheduled(cron = "${offermart.ingestion.cron:0 0 2 * * ?}")
    public void startOffermartDataIngestion() {
        log.info("Starting Offermart data ingestion process...");
        long startTime = System.currentTimeMillis();

        try {
            // 1. Simulate fetching customer data from Offermart
            List<OffermartCustomerDTO> customerData = fetchCustomerDataFromOffermart();
            log.info("Fetched {} customer records from Offermart for ingestion.", customerData.size());

            // 2. Delegate customer data ingestion to the service layer
            offermartIngestionService.ingestCustomerData(customerData);

            // 3. Simulate fetching offer data from Offermart
            List<OffermartOfferDTO> offerData = fetchOfferDataFromOffermart();
            log.info("Fetched {} offer records from Offermart for ingestion.", offerData.size());

            // 4. Delegate offer data ingestion to the service layer
            offermartIngestionService.ingestOfferData(offerData);

            log.info("Offermart data ingestion process completed successfully in {} ms.", (System.currentTimeMillis() - startTime));

        } catch (Exception e) {
            // Comprehensive error logging, potentially triggering alerts or metrics
            log.error("An unexpected error occurred during Offermart data ingestion process: {}", e.getMessage(), e);
            // Depending on the system's resilience requirements,
            // consider rethrowing a custom exception or publishing a failure event.
        }
    }

    /**
     * Simulates fetching customer data from the Offermart system.
     * In a real application, this method would contain the actual integration logic:
     * - Making REST API calls to Offermart's data export endpoint.
     * - Reading from a file (e.g., CSV, JSON) provided by Offermart via SFTP or cloud storage.
     * - Consuming messages from a dedicated Offermart data queue (e.g., Kafka topic).
     *
     * @return A list of {@link OffermartCustomerDTO} representing customer records retrieved from Offermart.
     */
    private List<OffermartCustomerDTO> fetchCustomerDataFromOffermart() {
        log.debug("Simulating fetching customer data from Offermart...");
        List<OffermartCustomerDTO> customers = new ArrayList<>();
        // Generate some dummy data for demonstration purposes
        customers.add(new OffermartCustomerDTO(UUID.randomUUID().toString(), "John", "Doe", "ABCDE1234F", "9876543210", "john.doe@example.com", LocalDate.of(1985, 1, 15)));
        customers.add(new OffermartCustomerDTO(UUID.randomUUID().toString(), "Jane", "Smith", "FGHIJ5678K", "9988776655", "jane.smith@example.com", LocalDate.of(1990, 5, 20)));
        customers.add(new OffermartCustomerDTO(UUID.randomUUID().toString(), "Alice", "Johnson", "KLMNO9012L", "9123456789", "alice.j@example.com", LocalDate.of(1978, 11, 30)));
        // Add a customer with missing mobile for validation test in OffermartIngestionServiceImpl
        customers.add(new OffermartCustomerDTO(UUID.randomUUID().toString(), "Bob", "Brown", "PQRST3456M", null, "bob.b@example.com", LocalDate.of(1992, 3, 10)));
        // Add a customer with missing ID for validation test in OffermartIngestionServiceImpl
        customers.add(new OffermartCustomerDTO(null, "Charlie", "Davis", "UVWXY7890N", "9000000000", "charlie.d@example.com", LocalDate.of(1980, 7, 25)));
        // Add a customer with missing PAN for validation test
        customers.add(new OffermartCustomerDTO(UUID.randomUUID().toString(), "Eve", "White", null, "9111111111", "eve.w@example.com", LocalDate.of(1995, 9, 5)));
        return customers;
    }

    /**
     * Simulates fetching offer data from the Offermart system.
     * Similar to customer data fetching, this would involve actual integration
     * with Offermart's offer data source (e.g., API, file, message queue).
     *
     * @return A list of {@link OffermartOfferDTO} representing offer records retrieved from Offermart.
     */
    private List<OffermartOfferDTO> fetchOfferDataFromOffermart() {
        log.debug("Simulating fetching offer data from Offermart...");
        List<OffermartOfferDTO> offers = new ArrayList<>();
        // Generate some dummy data for demonstration purposes
        String customerId1 = "cust-123"; // Example customer ID (could link to a dummy customer above)
        String customerId2 = "cust-456";
        String customerId3 = "cust-789";

        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId1, "Preapproved", 150000.00, "CAMP001", LocalDate.now(), LocalDate.now().plusMonths(1)));
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId1, "Loyalty", 50000.00, "CAMP002", LocalDate.now(), LocalDate.now().plusMonths(1)));
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId2, "E-aggregator", 200000.00, "CAMP003", LocalDate.now(), LocalDate.now().plusMonths(2)));
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId3, "Top-up", 75000.00, "CAMP004", LocalDate.now(), LocalDate.now().plusMonths(1)));
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId3, "Top-up", 80000.00, "CAMP004", LocalDate.now(), LocalDate.now().plusMonths(1))); // Another top-up for same customer
        // Add an offer with missing ID for validation test
        offers.add(new OffermartOfferDTO(null, customerId1, "Preapproved", 100000.00, "CAMP005", LocalDate.now(), LocalDate.now().plusMonths(1)));
        // Add an offer with invalid amount for validation test
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId2, "Loyalty", -10000.00, "CAMP006", LocalDate.now(), LocalDate.now().plusMonths(1)));
        // Add an offer with missing loan type for validation test
        offers.add(new OffermartOfferDTO(UUID.randomUUID().toString(), customerId3, null, 120000.00, "CAMP007", LocalDate.now(), LocalDate.now().plusMonths(1)));
        return offers;
    }
}