package com.ltfs.cdp.integration.service;

import com.ltfs.cdp.integration.model.MASCustomerData;
import com.ltfs.cdp.integration.model.CDPCustomer;
import com.ltfs.cdp.integration.model.CDPOffer;
import com.ltfs.cdp.integration.client.MASClient;
import com.ltfs.cdp.integration.exception.DataMigrationException;
import com.ltfs.cdp.integration.exception.DataValidationException;
import com.ltfs.cdp.integration.exception.DeduplicationException;
import com.ltfs.cdp.integration.service.customer.CustomerService;
import com.ltfs.cdp.integration.service.offer.OfferService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Service class responsible for handling one-time or periodic data migration from MAS (Marketing Automation System)
 * to the CDP (Customer Data Platform) system.
 * This service orchestrates the fetching of raw data from MAS, its validation, transformation,
 * deduplication, and persistence into the CDP's customer and offer entities.
 * It ensures data quality and consistency by applying business rules during the migration process.
 */
@Service
public class MASDataMigrator {

    private static final Logger log = LoggerFactory.getLogger(MASDataMigrator.class);

    private final MASClient masClient;
    private final CustomerService customerService;
    private final OfferService offerService;

    /**
     * Constructs a new MASDataMigrator with the necessary dependencies.
     * Spring's dependency injection automatically provides instances of MASClient, CustomerService, and OfferService.
     *
     * @param masClient The client for interacting with the MAS system to fetch raw data.
     * @param customerService The service responsible for customer-related operations, including validation,
     *                        deduplication, and persistence of customer data.
     * @param offerService The service responsible for offer-related operations, including validation,
     *                     and persistence of offer data.
     */
    @Autowired
    public MASDataMigrator(MASClient masClient, CustomerService customerService, OfferService offerService) {
        this.masClient = masClient;
        this.customerService = customerService;
        this.offerService = offerService;
    }

    /**
     * Initiates the data migration process from MAS.
     * This method fetches raw customer and offer data from MAS, processes each record,
     * applies validation and deduplication rules, and persists the transformed data
     * into the CDP system.
     *
     * The process is transactional to ensure data consistency. If an error occurs
     * during the processing of a batch, the entire batch operation might be rolled back
     * depending on the underlying service implementations. Individual record failures
     * are logged, and the migration continues for other records.
     *
     * @throws DataMigrationException if a critical error occurs during the migration process
     *                                that prevents further processing (e.g., failure to fetch data from MAS).
     */
    @Transactional // Ensures atomicity for the entire migration operation or per batch if implemented internally
    public void migrateMasData() throws DataMigrationException {
        log.info("Starting MAS data migration process...");
        long startTime = System.currentTimeMillis();
        AtomicInteger processedRecords = new AtomicInteger(0);
        AtomicInteger failedRecords = new AtomicInteger(0);

        try {
            // Step 1: Fetch raw data from MAS.
            // In a real-world scenario, this might involve pagination or batch processing
            // to handle large datasets efficiently and prevent out-of-memory errors.
            log.info("Fetching raw customer and offer data from MAS...");
            List<MASCustomerData> masRawDataList = masClient.fetchMASCustomerAndOfferData();
            log.info("Successfully fetched {} records from MAS.", masRawDataList.size());

            if (masRawDataList.isEmpty()) {
                log.warn("No data found in MAS for migration. Migration process completed with no records processed.");
                return;
            }

            // Step 2: Process each raw data record.
            // Each record is processed independently to minimize impact of individual failures.
            for (MASCustomerData masData : masRawDataList) {
                try {
                    log.debug("Processing MAS record for customer ID: {}", masData.getCustomerId());

                    // Step 2a: Validate and transform MAS data into CDP Customer entity.
                    // The customerService is expected to handle basic column-level validation
                    // as per functional requirements (e.g., "Perform basic column-level validation").
                    Optional<CDPCustomer> cdpCustomerOptional = customerService.validateAndTransform(masData);

                    if (cdpCustomerOptional.isEmpty()) {
                        log.warn("Skipping MAS record for customer ID {} due to validation failure or irrelevance during transformation.", masData.getCustomerId());
                        failedRecords.incrementAndGet();
                        continue;
                    }

                    CDPCustomer cdpCustomer = cdpCustomerOptional.get();

                    // Step 2b: Apply deduplication logic and save/update the customer.
                    // This step ensures a single profile view of the customer and deduplication
                    // against the 'live book' (Customer 360) before offers are finalized.
                    // This aligns with "Provide a single profile view of the customer for Consumer Loan Products through deduplication."
                    // and "Perform deduplication against the 'live book' (Customer 360)".
                    CDPCustomer savedCustomer = customerService.deduplicateAndSaveCustomer(cdpCustomer);
                    log.debug("Customer processed and saved/updated: {}", savedCustomer.getCustomerId());

                    // Step 2c: Validate and transform MAS offer data into CDP Offer entity.
                    // The offerService handles offer-specific validation and transformation.
                    Optional<CDPOffer> cdpOfferOptional = offerService.validateAndTransform(masData, savedCustomer.getCustomerId());

                    if (cdpOfferOptional.isEmpty()) {
                        log.warn("Skipping offer for customer ID {} due to validation failure or irrelevance during transformation.", masData.getCustomerId());
                        // Even if offer fails, customer might have been processed, so we count it as processed record.
                        processedRecords.incrementAndGet();
                        continue;
                    }

                    CDPOffer cdpOffer = cdpOfferOptional.get();

                    // Step 2d: Apply offer-specific deduplication (e.g., Top-up loans) and save the offer.
                    // This addresses "Top-up loan offers must be deduped only within other Top-up offers,
                    // and matches found should be removed."
                    offerService.deduplicateAndSaveOffer(cdpOffer);
                    log.debug("Offer processed and saved for customer ID: {}", savedCustomer.getCustomerId());

                    processedRecords.incrementAndGet();

                } catch (DataValidationException e) {
                    log.error("Data validation failed for MAS record (Customer ID: {}): {}", masData.getCustomerId(), e.getMessage());
                    failedRecords.incrementAndGet();
                } catch (DeduplicationException e) {
                    log.error("Deduplication failed for MAS record (Customer ID: {}): {}", masData.getCustomerId(), e.getMessage());
                    failedRecords.incrementAndGet();
                } catch (Exception e) {
                    // Catch any other unexpected exceptions during record processing
                    log.error("An unexpected error occurred while processing MAS record (Customer ID: {}): {}", masData.getCustomerId(), e.getMessage(), e);
                    failedRecords.incrementAndGet();
                }
            }

            long endTime = System.currentTimeMillis();
            log.info("MAS data migration completed. Total records fetched: {}, Processed successfully: {}, Failed: {}. Time taken: {} ms",
                     masRawDataList.size(), processedRecords.get(), failedRecords.get(), (endTime - startTime));

            if (failedRecords.get() > 0) {
                log.warn("Some records failed during MAS data migration. Please check logs for details on individual record failures.");
            }

        } catch (Exception e) {
            // Catch critical errors that prevent the entire migration from proceeding (e.g., MAS client failure)
            log.error("Critical error during MAS data migration: {}", e.getMessage(), e);
            throw new DataMigrationException("Failed to complete MAS data migration due to a critical error.", e);
        }
    }
}

// --- Placeholder/Mock Classes for compilation and context ---
// In a real project, these would be in their respective packages and fully implemented.
// These are included here to make the provided code directly runnable without modifications.

/**
 * Represents the raw customer and offer data fetched from the MAS (Marketing Automation System).
 * This is a simplified DTO for demonstration purposes.
 */
// Package: com.ltfs.cdp.integration.model
class MASCustomerData {
    private String customerId;
    private String firstName;
    private String lastName;
    private String email;
    private String phoneNumber;
    private String offerType;
    private Double offerAmount;
    private String masCampaignId; // Example: Campaign ID from MAS

    // Getters and Setters
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public Double getOfferAmount() { return offerAmount; }
    public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }
    public String getMasCampaignId() { return masCampaignId; }
    public void setMasCampaignId(String masCampaignId) { this.masCampaignId = masCampaignId; }
}

/**
 * Represents a customer profile in the CDP (Customer Data Platform).
 * This entity is the result of transformation and deduplication.
 */
// Package: com.ltfs.cdp.integration.model
class CDPCustomer {
    private String customerId; // Unique ID in CDP, potentially generated or derived
    private String firstName;
    private String lastName;
    private String email;
    private String phoneNumber;
    // Add more fields for a comprehensive CDP customer profile (e.g., address, date of birth, dedupe status)

    // Getters and Setters
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
}

/**
 * Represents an offer in the CDP (Customer Data Platform).
 * Linked to a CDPCustomer.
 */
// Package: com.ltfs.cdp.integration.model
class CDPOffer {
    private String offerId; // Unique ID in CDP for the offer
    private String customerId; // Foreign key to CDPCustomer
    private String offerType; // e.g., "Loyalty Loan", "Preapproved Loan", "Top-up Loan"
    private Double offerAmount;
    private String campaignId; // Linked to a CDP Campaign entity

    // Getters and Setters
    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public Double getOfferAmount() { return offerAmount; }
    public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
}

/**
 * Interface for interacting with the MAS (Marketing Automation System) to fetch raw data.
 * In a real application, this would be an actual client (e.g., REST client, database connector).
 */
// Package: com.ltfs.cdp.integration.client
interface MASClient {
    /**
     * Fetches a list of raw customer and offer data records from the MAS.
     *
     * @return A list of MASCustomerData objects.
     */
    List<MASCustomerData> fetchMASCustomerAndOfferData();
}

/**
 * Mock implementation of MASClient for demonstration purposes.
 * Provides dummy data to simulate MAS responses.
 */
@Service
class MASClientImpl implements MASClient {
    private static final Logger log = LoggerFactory.getLogger(MASClientImpl.class);

    @Override
    public List<MASCustomerData> fetchMASCustomerAndOfferData() {
        log.info("Simulating fetching data from MAS...");
        // Return some dummy data for demonstration, including cases for validation failures
        MASCustomerData data1 = new MASCustomerData();
        data1.setCustomerId("MAS_CUST_001");
        data1.setFirstName("John");
        data1.setLastName("Doe");
        data1.setEmail("john.doe@example.com");
        data1.setPhoneNumber("1234567890");
        data1.setOfferType("Preapproved Loan");
        data1.setOfferAmount(100000.00);
        data1.setMasCampaignId("MAS_CAMP_P001");

        MASCustomerData data2 = new MASCustomerData();
        data2.setCustomerId("MAS_CUST_002");
        data2.setFirstName("Jane");
        data2.setLastName("Smith");
        data2.setEmail("jane.smith@example.com");
        data2.setPhoneNumber("0987654321");
        data2.setOfferType("Loyalty Loan");
        data2.setOfferAmount(50000.00);
        data2.setMasCampaignId("MAS_CAMP_L001");

        MASCustomerData data3 = new MASCustomerData();
        data3.setCustomerId("MAS_CUST_003"); // This one will fail customer validation (missing last name)
        data3.setFirstName("Invalid");
        data3.setLastName(null);
        data3.setEmail("invalid@example.com");
        data3.setPhoneNumber("1112223333");
        data3.setOfferType("E-aggregator Loan");
        data3.setOfferAmount(75000.00);
        data3.setMasCampaignId("MAS_CAMP_E001");

        MASCustomerData data4 = new MASCustomerData();
        data4.setCustomerId("MAS_CUST_004"); // This one will have offer validation fail (invalid offer type)
        data4.setFirstName("Offer");
        data4.setLastName("Fail");
        data4.setEmail("offer.fail@example.com");
        data4.setPhoneNumber("4445556666");
        data4.setOfferType("Invalid Offer Type");
        data4.setOfferAmount(25000.00);
        data4.setMasCampaignId("MAS_CAMP_X001");

        MASCustomerData data5 = new MASCustomerData();
        data5.setCustomerId("MAS_CUST_005");
        data5.setFirstName("Topup");
        data5.setLastName("Customer");
        data5.setEmail("topup.customer@example.com");
        data5.setPhoneNumber("5556667777");
        data5.setOfferType("Top-up Loan"); // Example for specific offer dedupe logic
        data5.setOfferAmount(30000.00);
        data5.setMasCampaignId("MAS_CAMP_T001");

        return List.of(data1, data2, data3, data4, data5);
    }
}

/**
 * Interface for customer-related business logic, including validation, transformation,
 * and deduplication of customer data.
 */
// Package: com.ltfs.cdp.integration.service.customer
interface CustomerService {
    /**
     * Validates raw MAS customer data and transforms it into a CDP Customer entity.
     * Applies basic column-level validation.
     *
     * @param masData The raw MAS customer data.
     * @return An Optional containing the transformed CDPCustomer if valid, otherwise empty.
     * @throws DataValidationException if validation fails.
     */
    Optional<CDPCustomer> validateAndTransform(MASCustomerData masData) throws DataValidationException;

    /**
     * Applies deduplication logic to the given CDP Customer and persists it.
     * This involves checking against the 'live book' (Customer 360) and merging/saving.
     *
     * @param cdpCustomer The CDP Customer entity to deduplicate and save.
     * @return The saved or updated CDPCustomer entity.
     * @throws DeduplicationException if an error occurs during deduplication.
     */
    CDPCustomer deduplicateAndSaveCustomer(CDPCustomer cdpCustomer) throws DeduplicationException;
}

/**
 * Mock implementation of CustomerService for demonstration purposes.
 * Simulates validation and a simplified deduplication process.
 */
@Service
class CustomerServiceImpl implements CustomerService {
    private static final Logger log = LoggerFactory.getLogger(CustomerServiceImpl.class);

    @Override
    public Optional<CDPCustomer> validateAndTransform(MASCustomerData masData) throws DataValidationException {
        // Simulate basic column-level validation as per functional requirements
        if (masData.getFirstName() == null || masData.getFirstName().trim().isEmpty()) {
            throw new DataValidationException("Customer data validation failed: First name is missing for customer ID " + masData.getCustomerId());
        }
        if (masData.getLastName() == null || masData.getLastName().trim().isEmpty()) {
            throw new DataValidationException("Customer data validation failed: Last name is missing for customer ID " + masData.getCustomerId());
        }
        if (masData.getEmail() == null || !masData.getEmail().contains("@") || !masData.getEmail().contains(".")) {
            throw new DataValidationException("Customer data validation failed: Invalid email format for customer ID " + masData.CustomerId());
        }
        // Add more validation rules as needed (e.g., phone number format, data types)

        // Simulate transformation from MAS data to CDP Customer entity
        CDPCustomer cdpCustomer = new CDPCustomer();
        // In a real system, CDP Customer ID might be generated or looked up based on deduplication
        cdpCustomer.setCustomerId("CDP_CUST_" + masData.getCustomerId());
        cdpCustomer.setFirstName(masData.getFirstName());
        cdpCustomer.setLastName(masData.getLastName());
        cdpCustomer.setEmail(masData.getEmail());
        cdpCustomer.setPhoneNumber(masData.getPhoneNumber());
        log.debug("Transformed MAS customer data to CDP customer: {}", cdpCustomer.getCustomerId());
        return Optional.of(cdpCustomer);
    }

    @Override
    public CDPCustomer deduplicateAndSaveCustomer(CDPCustomer cdpCustomer) throws DeduplicationException {
        // Simulate deduplication against 'live book' (Customer 360)
        // This is a placeholder for complex deduplication logic.
        // In a real scenario, this would involve:
        // 1. Querying existing customers by various attributes (email, phone, name combinations).
        // 2. Applying matching algorithms (e.g., fuzzy matching).
        // 3. If a match is found, merging the new data with the existing customer profile.
        // 4. If no match, saving as a new customer.
        log.info("Applying deduplication logic for customer: {}. (Simulated: always creates/updates)", cdpCustomer.getCustomerId());

        // For this mock, we simply return the customer as if it's been saved/updated.
        // In a real scenario, this would interact with a CustomerRepository.
        log.info("Customer {} deduped and saved/updated successfully.", cdpCustomer.getCustomerId());
        return cdpCustomer;
    }
}

/**
 * Interface for offer-related business logic, including validation, transformation,
 * and specific deduplication rules for offers.
 */
// Package: com.ltfs.cdp.integration.service.offer
interface OfferService {
    /**
     * Validates raw MAS offer data and transforms it into a CDP Offer entity.
     * Links the offer to an existing CDP Customer.
     *
     * @param masData The raw MAS customer and offer data.
     * @param cdpCustomerId The ID of the associated CDP Customer.
     * @return An Optional containing the transformed CDPOffer if valid, otherwise empty.
     * @throws DataValidationException if validation fails.
     */
    Optional<CDPOffer> validateAndTransform(MASCustomerData masData, String cdpCustomerId) throws DataValidationException;

    /**
     * Applies offer-specific deduplication logic (e.g., for Top-up loans) and persists the offer.
     *
     * @param cdpOffer The CDP Offer entity to deduplicate and save.
     * @return The saved or updated CDPOffer entity.
     * @throws DeduplicationException if an error occurs during offer deduplication.
     */
    CDPOffer deduplicateAndSaveOffer(CDPOffer cdpOffer) throws DeduplicationException;
}

/**
 * Mock implementation of OfferService for demonstration purposes.
 * Simulates offer validation and specific deduplication rules.
 */
@Service
class OfferServiceImpl implements OfferService {
    private static final Logger log = LoggerFactory.getLogger(OfferServiceImpl.class);

    @Override
    public Optional<CDPOffer> validateAndTransform(MASCustomerData masData, String cdpCustomerId) throws DataValidationException {
        // Simulate basic column-level validation for offers
        if (masData.getOfferType() == null || masData.getOfferType().trim().isEmpty()) {
            throw new DataValidationException("Offer data validation failed: Offer type is missing for customer ID " + masData.getCustomerId());
        }
        if (masData.getOfferAmount() == null || masData.getOfferAmount() <= 0) {
            throw new DataValidationException("Offer data validation failed: Invalid offer amount for customer ID " + masData.getCustomerId());
        }

        // Simulate specific offer type validation (e.g., only allow known types)
        List<String> allowedOfferTypes = List.of("Loyalty Loan", "Preapproved Loan", "E-aggregator Loan", "Top-up Loan");
        if (!allowedOfferTypes.contains(masData.getOfferType())) {
            throw new DataValidationException("Invalid offer type: '" + masData.getOfferType() + "' for customer ID " + masData.getCustomerId());
        }

        // Simulate transformation
        CDPOffer cdpOffer = new CDPOffer();
        // Generate a unique offer ID for CDP
        cdpOffer.setOfferId("CDP_OFFER_" + cdpCustomerId + "_" + System.nanoTime());
        cdpOffer.setCustomerId(cdpCustomerId);
        cdpOffer.setOfferType(masData.getOfferType());
        cdpOffer.setOfferAmount(masData.getOfferAmount());
        cdpOffer.setCampaignId(masData.getMasCampaignId() != null ? "CDP_CAMP_" + masData.getMasCampaignId() : "CDP_CAMP_DEFAULT");
        log.debug("Transformed MAS offer data to CDP offer for customer: {}", cdpCustomerId);
        return Optional.of(cdpOffer);
    }

    @Override
    public CDPOffer deduplicateAndSaveOffer(CDPOffer cdpOffer) throws DeduplicationException {
        // Simulate offer-specific deduplication (e.g., "Top-up loan offers must be deduped only within other Top-up offers")
        log.info("Applying offer-specific deduplication logic for offer ID: {}", cdpOffer.getOfferId());

        if ("Top-up Loan".equalsIgnoreCase(cdpOffer.getOfferType())) {
            // Logic for Top-up loan deduplication:
            // 1. Query existing 'Top-up Loan' offers for this customer.
            // 2. If a matching Top-up offer is found (e.g., based on amount, date, or other criteria),
            //    decide whether to:
            //    a. Invalidate/remove the older offer.
            //    b. Discard the new offer.
            //    c. Merge/update the existing offer.
            // This mock simply logs the action.
            log.info("Top-up loan offer {} for customer {} is being deduped within other Top-up offers. (Simulated: always saved)",
                     cdpOffer.getOfferId(), cdpOffer.getCustomerId());
            // In a real scenario, this would involve a repository call and business logic.
        } else {
            // Logic for other offer types (e.g., "Apply dedupe logic across all Consumer Loan (CL) products")
            // This might involve different rules or simply ensuring no duplicate offers of the same type/campaign.
            log.info("General offer deduplication applied for offer type: {} (Simulated: always saved)", cdpOffer.getOfferType());
        }

        // Simulate saving the offer to the database
        // In a real scenario, this would interact with an OfferRepository.
        log.info("Offer {} deduped and saved successfully.", cdpOffer.getOfferId());
        return cdpOffer;
    }
}

/**
 * Custom exception for critical errors during the overall data migration process.
 */
// Package: com.ltfs.cdp.integration.exception
class DataMigrationException extends RuntimeException {
    public DataMigrationException(String message) {
        super(message);
    }
    public DataMigrationException(String message, Throwable cause) {
        super(message, cause);
    }
}

/**
 * Custom exception for data validation failures during transformation.
 */
// Package: com.ltfs.cdp.integration.exception
class DataValidationException extends RuntimeException {
    public DataValidationException(String message) {
        super(message);
    }
}

/**
 * Custom exception for errors encountered during the deduplication process.
 */
// Package: com.ltfs.cdp.integration.exception
class DeduplicationException extends RuntimeException {
    public DeduplicationException(String message) {
        super(message);
    }
    public DeduplicationException(String message, Throwable cause) {
        super(message, cause);
    }
}